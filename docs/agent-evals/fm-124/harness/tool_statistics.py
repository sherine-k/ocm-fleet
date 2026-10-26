"""Count recorded activity, without model interpretation or new model calls.

The pre-edit window ends before the enclosing tool call of the first successful
FileChange event. Shell writes are not file-watched; this is a recorded-patch
boundary, not a general filesystem audit. Ambiguous/missing boundaries stay null.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from context_usage import analyze


def counts(values):
    return dict(sorted(Counter(values).items()))


def summarize(records, analysis):
    calls, executions, active = [], [], {}
    first_edit = None
    cutoff = None
    seen = set()
    request_by_call = {item["call_id"]: item["issued_request"]
                       for item in analysis["tool_calls"]}
    for index, record in enumerate(records):
        payload = record.get("payload", {})
        kind = payload.get("type")
        if record["type"] == "response_item":
            if kind in ("function_call", "custom_tool_call"):
                call = {"record_number": index + 1, "call_id": payload["call_id"],
                        "tool_name": payload["name"]}
                calls.append(call)
                active[call["call_id"]] = call
            elif kind in ("function_call_output", "custom_tool_call_output"):
                active.pop(payload["call_id"], None)
        if record["type"] != "event_msg" or kind != "item_completed":
            continue
        item = payload["item"]
        if item["type"] not in ("CommandExecution", "FileChange"):
            continue
        if item["id"] in seen:
            raise ValueError(f"Duplicate execution: {item['id']}")
        seen.add(item["id"])
        parsed = item.get("parsed_cmd", [])
        skills = sorted({Path(part["path"]).parent.name for part in parsed
                         if part.get("type") == "read" and part.get("path")
                         and Path(part["path"]).name == "SKILL.md"})
        execution = {
            "record_number": index + 1, "id": item["id"], "type": item["type"],
            "status": item["status"], "exit_code": item.get("exit_code"),
            "command": item.get("command"),
            "logged_command_kinds": sorted({part["type"] for part in parsed}),
            "skill_reads": skills if item.get("exit_code") == 0
                           and item.get("aggregated_output", "").strip() else [],
        }
        executions.append(execution)
        if item["type"] == "FileChange" and item["status"] == "completed" and first_edit is None:
            first_edit = {"event_id": item["id"], "record_number": index + 1,
                          "status": "ambiguous enclosing tool call",
                          "call_id": None, "request_number": None}
            if len(active) == 1:
                call = next(iter(active.values()))
                cutoff = call["record_number"]
                first_edit.update(status="recorded FileChange", call_id=call["call_id"],
                                  request_number=request_by_call[call["call_id"]])

    def aggregate(window_calls, window_executions):
        commands = [item for item in window_executions if item["type"] == "CommandExecution"]
        patches = [item for item in window_executions if item["type"] == "FileChange"]
        skills = [name for item in commands for name in item["skill_reads"]]
        return {
            "tool_calls": len(window_calls),
            "tool_calls_by_name": counts(item["tool_name"] for item in window_calls),
            "shell_commands": len(commands),
            "shell_exit_codes": counts(str(item["exit_code"]) for item in commands),
            "nonzero_shell_exits": sum(item["exit_code"] is not None and item["exit_code"] != 0
                                       for item in commands),
            "unknown_shell_exits": sum(item["exit_code"] is None for item in commands),
            "commands_by_logged_kind": counts(kind for item in commands for kind in item["logged_command_kinds"]),
            "recognized_skill_reads": len(skills), "skill_reads_by_name": counts(skills),
            "file_change_events": len(patches),
            "file_change_events_by_status": counts(item["status"] for item in patches),
        }

    def checkpoint(row):
        return {key: row[key] for key in ("request_number", "input_tokens", "cached_input_tokens")}

    edit_request = first_edit["request_number"] if first_edit else None
    edit = next((row for row in analysis["requests"] if row["request_number"] == edit_request), None)
    return {
        "run": analysis["run"], "first_recorded_edit": first_edit,
        "context": {
            "checkpoints": {"initial_request": checkpoint(analysis["requests"][0]),
                            "before_first_edit": checkpoint(edit) if edit else None},
            "totals": analysis["totals"],
            "total_input_plus_output_tokens": analysis["totals"]["input_tokens"] + analysis["totals"]["output_tokens"],
            "requests": len(analysis["requests"]),
            "maximum_request_input_tokens": max(row["input_tokens"] for row in analysis["requests"]),
            "compactions_observed": analysis["compactions_observed"],
        },
        "overall": aggregate(calls, executions),
        "before_first_edit": aggregate(
            [item for item in calls if item["record_number"] < cutoff],
            [item for item in executions if item["record_number"] < cutoff],
        ) if cutoff is not None else None,
        "tool_call_ledger": calls, "execution_ledger": executions,
        "definitions": {
            "tokens": "Provider usage: cached input is included in input; reasoning is included in output. Initial input is the whole request. Accumulated input counts history repeatedly and is not context size or dollar cost.",
            "tool_calls": "Model-issued tool calls, grouped by name; nested shell executions are separate, not added to this total.",
            "shell_commands": "Actual completed CommandExecution events, once per ID; includes compound scripts, excludes polling calls and unobserved child processes.",
            "recognized_skill_reads": "Successful nonempty commands with a logger-classified read path ending in SKILL.md, once per skill per command. This is retrieval, not proof of semantic use; unclassified/indirect reads can be missed.",
            "commands_by_logged_kind": "Logger classifications, once per kind per shell command; categories may overlap and unknown is retained.",
            "before_first_edit": "Excludes the entire tool call enclosing the first successful FileChange event, including same-call reads. Shell-based writes are not detected. Missing/ambiguous boundaries are null.",
            "nonzero_shell_exits": "Observed nonzero exits, including intentional test failures and searches without matches; not a count of defects remaining.",
        },
    }


def assessment_statistics(directory):
    """Parse the pinned unittest/Vitest summary formats; never infer untested defects."""
    exits = json.loads((directory / "result.json").read_text())
    cli = (directory / "cli.log").read_text()
    stream = re.sub(r"\x1b\[[0-9;]*m", "", (directory / "stream.log").read_text())
    cli_total = re.findall(r"^Ran (\d+) tests? in ", cli, re.MULTILINE)
    stream_totals = re.findall(r"^\s*Tests\s+(.+?)\s+\((\d+)\)\s*$", stream, re.MULTILINE)
    if len(cli_total) != 1 or len(stream_totals) != 1:
        raise ValueError("Expected one unittest and one Vitest summary")
    failed_cli = re.findall(r"^FAILED \((.+)\)$", cli, re.MULTILINE)
    ok_cli = re.findall(r"^OK(?: \((.+)\))?$", cli, re.MULTILINE)
    if len(failed_cli) + len(ok_cli) != 1:
        raise ValueError("Missing unittest outcome")
    cli_failures = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", " ".join(failed_cli)))
    cli_skipped = sum(int(n) for n in re.findall(r"skipped=(\d+)", " ".join(failed_cli + ok_cli)))
    total = int(stream_totals[0][1])
    states = Counter()
    for n, state in re.findall(r"(\d+) (passed|failed|skipped|todo)", stream_totals[0][0]):
        states[state] += int(n)
    if sum(states.values()) != total:
        raise ValueError("Incomplete Vitest test totals")
    jobs = {
        "built_cli": {"total": int(cli_total[0]), "failed_or_error": cli_failures,
                      "skipped": cli_skipped, "exit_code": exits["cli_exit_code"]},
        "writable": {"total": total, "failed_or_error": states["failed"],
                     "skipped": states["skipped"] + states["todo"],
                     "exit_code": exits["stream_exit_code"]},
    }
    return {"jobs": jobs,
            "total": sum(job["total"] for job in jobs.values()),
            "failed_or_error": sum(job["failed_or_error"] for job in jobs.values()),
            "skipped": sum(job["skipped"] for job in jobs.values()),
            "nonzero_job_exits": sum(job["exit_code"] != 0 for job in jobs.values()),
            "scope": "Only the checks present in these logs; no inference about untested behavior."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollout", type=Path)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assessment", type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.rollout.read_text().splitlines()]
    result = summarize(records, analyze(records, args.run))
    paths = {"rollout": args.rollout}
    if args.assessment:
        result["assessment"] = assessment_statistics(args.assessment)
        paths.update({name: args.assessment / name for name in ("result.json", "cli.log", "stream.log")})
    result["sources"] = {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                         for name, path in paths.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if not key.endswith("_ledger")}, indent=2))


if __name__ == "__main__":
    main()
