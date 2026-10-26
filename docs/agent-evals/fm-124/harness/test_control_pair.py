import json
from pathlib import Path
import tempfile
import unittest
import subprocess

from control_pair import apply_guidance_tree, apply_lean_guidance, normalize


class SnapshotComparisonTests(unittest.TestCase):
    def test_only_envelope_identifiers_are_ignored(self):
        snapshot = [{"type": "additional_tools", "id": "volatile", "tools": [{
            "parameters": {"properties": {"id": {"type": "string"}}},
        }]}, {"type": "message", "id": "volatile",
              "internal_chat_message_metadata_passthrough": {"create_time": 123, "turn_id": "turn"},
              "content": [{"text": "/tmp/subject/AGENTS.md"}]}]
        result = normalize(snapshot, Path("/tmp/subject"))
        self.assertNotIn("id", result[0])
        self.assertIn("id", result[0]["tools"][0]["parameters"]["properties"])
        self.assertEqual(result[1]["content"][0]["text"], "<CHECKOUT>/AGENTS.md")
        self.assertEqual(result[1]["internal_chat_message_metadata_passthrough"], {})


class LeanGuidanceTests(unittest.TestCase):
    def test_changes_only_nx_guidance_and_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = """# Project
<!-- nx configuration start-->
old Nx rules
<!-- nx configuration end-->
## Domain
Keep this comment.
- Prefer running tasks through Nx (`npx nx run <project>:<target>`) duplicate
"""
            (root / "AGENTS.md").write_text(original)
            nested = root / "client/cli/AGENTS.md"
            nested.parent.mkdir(parents=True)
            nested.write_text("CLI guidance stays unchanged.\n")
            skill = root / ".agents/skills/nx-workspace"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("upstream skill")
            other = root / ".agents/skills/other"
            other.mkdir()
            (other / "SKILL.md").write_text("keep")
            for folder in (".claude", ".cursor"):
                link = root / folder / "skills/nx-workspace"
                link.parent.mkdir(parents=True)
                link.symlink_to("../../.agents/skills/nx-workspace")
            settings = root / ".claude/settings.json"
            settings.write_text(json.dumps({
                "extraKnownMarketplaces": {"nx-claude-plugins": {"source": "upstream"}},
                "enabledPlugins": {"nx@nx-claude-plugins": True},
            }))
            lock = root / "skills-lock.json"
            lock.write_text(json.dumps({"version": 1, "skills": {"nx-workspace": {}}}))
            lean = "## Nx\n\n- Use npx nx and https://nx.dev/docs.\n\n## Understanding the domain\n"
            apply_lean_guidance(root, lean)
            self.assertEqual((root / "AGENTS.md").read_text(), """# Project
## Nx

- Use npx nx and https://nx.dev/docs.
## Domain
Keep this comment.
""")
            self.assertEqual(nested.read_text(), "CLI guidance stays unchanged.\n")
            self.assertEqual((other / "SKILL.md").read_text(), "keep")
            self.assertFalse(skill.exists())
            self.assertFalse(settings.exists())
            self.assertFalse(lock.exists())
            for folder in (".claude", ".cursor"):
                self.assertFalse((root / folder / "skills/nx-workspace").is_symlink())

    def test_refuses_to_remove_unrelated_plugin_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("<!-- nx configuration start-->old<!-- nx configuration end-->")
            (root / ".claude").mkdir()
            settings = root / ".claude/settings.json"
            settings.write_text(json.dumps({"enabledPlugins": {"unrelated": True}}))
            with self.assertRaises(ValueError):
                apply_lean_guidance(root, "## Nx\nlean\n## Understanding the domain")
            self.assertTrue(settings.exists())


class CurrentGuidanceTests(unittest.TestCase):
    def test_copies_current_tracked_guides_without_application_or_build_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, checkout = (Path(temporary) / name for name in ("source", "subject"))
            source.mkdir()
            checkout.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            guide = "# New root\n## Nx\nUse npx nx.\n## Understanding the domain\nNew domain index.\n"
            (source / "AGENTS.md").write_text(guide)
            for name, text in (("client/cli/AGENTS.md", "New CLI policy"),
                               ("server/AGENTS.md", "Scoped server policy"),
                               ("client/cli/project.json", "new build configuration")):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            (source / "untracked/AGENTS.md").parent.mkdir()
            (source / "untracked/AGENTS.md").write_text("Do not copy incidental files")
            (checkout / "AGENTS.md").write_text(
                "<!-- nx configuration start-->old Nx<!-- nx configuration end-->\nOld domain")
            for name, text in (("client/cli/AGENTS.md", "Old CLI policy"),
                               ("obsolete/AGENTS.md", "Removed guide"),
                               ("client/cli/project.json", "historical build configuration"),
                               ("client/cli/main.ts", "historical application"),
                               (".agents/skills/nx-workspace/SKILL.md", "Nx skill")):
                path = checkout / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            hashes = apply_guidance_tree(checkout, source)
            self.assertEqual((checkout / "AGENTS.md").read_text(), guide)
            self.assertEqual((checkout / "client/cli/AGENTS.md").read_text(), "New CLI policy")
            self.assertEqual((checkout / "server/AGENTS.md").read_text(), "Scoped server policy")
            self.assertEqual((checkout / "client/cli/project.json").read_text(), "historical build configuration")
            self.assertEqual((checkout / "client/cli/main.ts").read_text(), "historical application")
            self.assertFalse((checkout / "obsolete/AGENTS.md").exists())
            self.assertFalse((checkout / "untracked/AGENTS.md").exists())
            self.assertFalse((checkout / ".agents/skills/nx-workspace").exists())
            self.assertEqual(set(hashes), {"AGENTS.md", "client/cli/AGENTS.md", "server/AGENTS.md"})


if __name__ == "__main__":
    unittest.main()
