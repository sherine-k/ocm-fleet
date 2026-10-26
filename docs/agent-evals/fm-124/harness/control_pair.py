"""Prepare isolated control or lean-guidance pairs, then capture fresh sessions.

All experimental Codex processes use the work profile. Startup snapshots make
no inference calls. Raw telemetry and subject repositories stay in the bundle.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from context_usage import analyze, checkpoint_summary


BASE = "775b87ed75af7dc1977240f6a220183504cd055d"
PROFILE = Path("/Users/ahenning/.codex-work")
ENV = dict(os.environ, CODEX_HOME=str(PROFILE), PYTHONDONTWRITEBYTECODE="1")
NX_SKILLS = ("link-workspace-packages", "monitor-ci", "nx-generate", "nx-import",
             "nx-plugins", "nx-run-tasks", "nx-workspace")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.run(command, env=ENV, check=True, **kwargs)


def common(checkout):
    return ["codex", "--no-daemon", "--search", "--approve-for-me", "-m", "gpt-6-luna",
            "-c", 'model_reasoning_effort="max"', "-C", str(checkout)]


def normalize(value, checkout, metadata=False):
    if isinstance(value, list):
        return [normalize(item, checkout) for item in value]
    if isinstance(value, dict):
        ignored = {"create_time", "turn_id", "session_id", "thread_id"} if metadata else set()
        if value.get("type") in ("message", "additional_tools"):
            ignored.add("id")
        return {key: normalize(item, checkout, key == "internal_chat_message_metadata_passthrough")
                for key, item in value.items() if key not in ignored}
    if isinstance(value, str):
        return value.replace(str(checkout), "<CHECKOUT>")
    return value


def snapshot(checkout, output, prompt):
    with output.open("w") as target:
        run(common(checkout) + ["debug", "prompt-input", prompt], stdout=target,
            stderr=subprocess.PIPE, text=True)


def apply_lean_guidance(checkout, lean):
    """Apply only the agreed Nx guidance change to the historical checkout."""
    settings = checkout / ".claude/settings.json"
    lock = checkout / "skills-lock.json"
    if settings.exists():
        config = json.loads(settings.read_text())
        if (set(config) - {"extraKnownMarketplaces", "enabledPlugins"}
                or set(config.get("extraKnownMarketplaces", {})) - {"nx-claude-plugins"}
                or set(config.get("enabledPlugins", {})) - {"nx@nx-claude-plugins"}):
            raise ValueError("Refusing to remove unrelated Claude settings")
    if lock.exists() and set(json.loads(lock.read_text())["skills"]) - set(NX_SKILLS):
        raise ValueError("Refusing to remove unrelated installed skills")
    section = lean[lean.index("## Nx\n"):lean.index("## Understanding the domain")].rstrip()
    guide = checkout / "AGENTS.md"
    updated, count = re.subn(r"<!-- nx configuration start-->.*?<!-- nx configuration end-->",
                             lambda _: section, guide.read_text(), count=1, flags=re.S)
    if count != 1:
        raise ValueError("Expected the historical Nx guidance block")
    updated = "\n".join(line for line in updated.split("\n")
                          if not line.startswith("- Prefer running tasks through Nx (`npx nx run"))
    guide.write_text(updated)
    for folder in (".agents", ".claude", ".cursor"):
        for skill in NX_SKILLS:
            path = checkout / folder / "skills" / skill
            if path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
    settings.unlink(missing_ok=True)
    lock.unlink(missing_ok=True)


def prepare(args):
    bundle = args.bundle.resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    assert not (bundle / "manifest.json").exists(), "Refusing to overwrite a prepared bundle"
    shutil.copy2(args.prompt, bundle / "prompt.txt")
    archive = bundle / "baseline.tar"
    with archive.open("wb") as output:
        run(["git", "-C", str(args.source), "archive", BASE], stdout=output)
    treatment = args.lean_agents is not None
    manifest = {
        "kind": "duplicate-lean-guidance-treatments-v2" if treatment else "duplicate-original-guidance-controls-v2", "source_commit": BASE,
        "archive_sha256": sha(archive), "prompt_sha256": sha(bundle / "prompt.txt"),
        "model": "gpt-6-luna", "reasoning_effort": "max", "codex_home": str(PROFILE),
        "cli_version": run(["codex", "--version"], capture_output=True, text=True).stdout.strip(),
        "context_measurement": "Initial request and input before first edit; provider-reported tokens",
        "runs": [],
    }
    if treatment:
        manifest["lean_agents_sha256"] = sha(args.lean_agents)
    prompt = (bundle / "prompt.txt").read_text()
    for name in (f"{'treatment' if treatment else 'control'}-{number}" for number in (1, 2)):
        checkout = bundle / name
        checkout.mkdir()
        run(["tar", "-xf", str(archive), "-C", str(checkout)])
        if treatment:
            apply_lean_guidance(checkout, args.lean_agents.read_text())
        run(["git", "init", "-q"], cwd=checkout)
        run(["git", "add", "."], cwd=checkout)
        run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "FM-124 historical baseline"], cwd=checkout)
        run(["cp", "-cR", str(args.source / "node_modules"), str(checkout / "node_modules")])
        for link in (checkout / "node_modules/@ocm-fleet").iterdir():
            assert link.is_symlink() and link.resolve().is_relative_to(checkout)
        for path in checkout.rglob("package.json"):
            if "node_modules" not in path.parts:
                source = args.source / path.relative_to(checkout)
                assert source.exists() and sha(path) == sha(source), path
        assert sha(checkout / "package-lock.json") == sha(args.source / "package-lock.json")
        artifact = bundle / "artifacts" / name
        artifact.mkdir(parents=True)
        snapshot(checkout, artifact / "initial-input.json", prompt)
        guidance = {str(path.relative_to(checkout)): sha(path) for path in checkout.rglob("*.md")
                    if "node_modules" not in path.parts and (path.name in ("AGENTS.md", "SKILL.md"))}
        (artifact / "guidance-hashes.json").write_text(json.dumps(guidance, indent=2) + "\n")
        entry = {"name": name, "checkout": str(checkout), "artifacts": str(artifact),
                 "initial_snapshot_sha256": sha(artifact / "initial-input.json")}
        manifest["runs"].append(entry)
        print("Prepared", name, flush=True)
    controls = manifest["runs"]
    normalized = [normalize(json.loads((Path(item["artifacts"]) / "initial-input.json").read_text()),
                            Path(item["checkout"])) for item in controls]
    assert normalized[0] == normalized[1], "Pair initial inputs differ"
    manifest["normalized_pair_inputs_equal"] = True
    manifest["profile_guidance_sha256"] = sha(PROFILE / "AGENTS.md")
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Ready:", bundle, flush=True)


def capture_patch(checkout, artifact):
    with (artifact / "changes.patch").open("wb") as patch:
        run(["git", "diff", "--binary", "HEAD"], cwd=checkout, stdout=patch)
        untracked = run(["git", "ls-files", "--others", "--exclude-standard", "-z"],
                        cwd=checkout, capture_output=True).stdout
        for path in untracked.decode().split("\0"):
            if path:
                result = subprocess.run(["git", "diff", "--no-index", "--binary", "--", "/dev/null", path],
                                        cwd=checkout, stdout=patch, env=ENV)
                assert result.returncode in (0, 1), path
    with (artifact / "status.txt").open("w") as output:
        run(["git", "status", "--short"], cwd=checkout, stdout=output)


def capture(args):
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert sha(bundle / "prompt.txt") == manifest["prompt_sha256"]
    assert sha(PROFILE / "AGENTS.md") == manifest["profile_guidance_sha256"]
    processes = []
    executor = ThreadPoolExecutor(max_workers=2)
    def wait_for_process(process, started):
        exit_code = process.wait()
        return {"exit_code": exit_code, "elapsed_seconds": round(time.monotonic() - started, 3),
                "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for entry in manifest["runs"]:
        checkout, artifact = Path(entry["checkout"]), Path(entry["artifacts"])
        assert not (artifact / "run.json").exists(), "Never overwrite an experimental run"
        command = common(checkout) + ["exec", "--json", "--color", "never", "-o", str(artifact / "final.md"), "-"]
        metadata = {"command": command, "CODEX_HOME": str(PROFILE),
                    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        with (bundle / "prompt.txt").open() as prompt, (artifact / "events.jsonl").open("w") as events, (artifact / "stderr.log").open("w") as errors:
            process = subprocess.Popen(command, cwd=checkout, env=ENV, stdin=prompt, stdout=events, stderr=errors)
        metadata["pid"] = process.pid
        (artifact / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        future = executor.submit(wait_for_process, process, time.monotonic())
        processes.append((future, entry, metadata))
        print("Started", entry["name"], "pid", process.pid, flush=True)
    by_future = {future: (entry, metadata) for future, entry, metadata in processes}
    for future in as_completed(by_future):
        entry, metadata = by_future[future]
        metadata.update(future.result())
        artifact, checkout = Path(entry["artifacts"]), Path(entry["checkout"])
        (artifact / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        capture_patch(checkout, artifact)
        events = [json.loads(line) for line in (artifact / "events.jsonl").read_text().splitlines()]
        thread = next(event["thread_id"] for event in events if event.get("type") == "thread.started")
        rollouts = list((PROFILE / "sessions").rglob("*" + thread + "*.jsonl"))
        assert len(rollouts) == 1, rollouts
        shutil.copy2(rollouts[0], artifact / "rollout.jsonl")
        records = [json.loads(line) for line in (artifact / "rollout.jsonl").read_text().splitlines()]
        analysis = analyze(records, entry["name"])
        (artifact / "context-usage.json").write_text(json.dumps(analysis, indent=2) + "\n")
        (artifact / "checkpoints.json").write_text(json.dumps(checkpoint_summary(analysis), indent=2) + "\n")
        print("Completed", entry["name"], metadata["exit_code"], analysis["totals"], flush=True)
    executor.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "capture"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--lean-agents", type=Path, help="Prepare lean-guidance treatments instead of controls")
    args = parser.parse_args()
    (prepare if args.action == "prepare" else capture)(args)


if __name__ == "__main__":
    main()
