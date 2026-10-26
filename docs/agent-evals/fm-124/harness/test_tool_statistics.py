"""Mechanical activity counts from the recorded Codex event schema."""
import unittest
import json
from pathlib import Path
import tempfile

from context_usage import analyze
from test_context_usage import call, output, record, usage
from tool_statistics import assessment_statistics, summarize


def item(kind, identifier, **fields):
    return record("event_msg", {"type": "item_completed", "item": {
        "type": kind, "id": identifier, **fields,
    }})


def command(identifier, exit_code=0, parsed=None, text="content"):
    return item("CommandExecution", identifier, exit_code=exit_code,
                command=["bash", "-lc", "cat file"], status="completed",
                parsed_cmd=parsed or [{"type": "read", "path": "file"}],
                aggregated_output=text)


class ToolStatisticsTests(unittest.TestCase):
    def summary(self, records):
        return summarize(records, analyze(records, "test"))

    def test_actual_executions_not_javascript_mentions_or_poll_calls(self):
        records = [call("read", 'cmds.map(cmd => tools.exec_command({cmd}))'),
                   usage("1", 100, 100), command("a"), command("b", exit_code=1),
                   output("read", "done"),
                   call("poll", 'await tools.write_stdin({session_id:1})'),
                   usage("2", 120, 220), output("poll", "done")]
        stats = self.summary(records)["overall"]
        self.assertEqual(stats["tool_calls_by_name"], {"exec": 2})
        self.assertEqual(stats["shell_commands"], 2)
        self.assertEqual(stats["nonzero_shell_exits"], 1)
        self.assertEqual(stats["shell_exit_codes"], {"0": 1, "1": 1})

    def test_edit_boundary_excludes_edit_request_even_when_it_also_reads(self):
        records = [call("read", "read"), usage("1", 100, 100), command("a"),
                   output("read", "done"), call("edit", "edit and read"),
                   usage("2", 140, 240), command("same-batch"),
                   item("FileChange", "patch", status="completed"),
                   output("edit", "done"), call("later", "later"),
                   usage("3", 180, 420), command("c", exit_code=2)]
        stats = self.summary(records)
        self.assertEqual(stats["first_recorded_edit"]["request_number"], 2)
        self.assertEqual(stats["before_first_edit"]["tool_calls"], 1)
        self.assertEqual(stats["before_first_edit"]["shell_commands"], 1)
        self.assertEqual(stats["before_first_edit"]["nonzero_shell_exits"], 0)
        self.assertEqual(stats["overall"]["shell_commands"], 3)
        context = stats["context"]
        self.assertEqual(context["checkpoints"]["initial_request"]["input_tokens"], 100)
        self.assertEqual(context["checkpoints"]["before_first_edit"]["input_tokens"], 140)
        self.assertEqual(context["total_input_plus_output_tokens"], 423)
        self.assertEqual(context["maximum_request_input_tokens"], 180)
        self.assertEqual(context["requests"], 3)

    def test_skill_reads_require_read_classification_success_and_output(self):
        skill = {"type": "read", "path": ".agents/skills/nx-workspace/SKILL.md"}
        records = [call("a", "read"), usage("1", 100, 100),
                   command("read", parsed=[skill]),
                   command("again", parsed=[skill]),
                   command("failed", exit_code=1, parsed=[skill]),
                   command("empty", parsed=[skill], text=""),
                   command("listing", parsed=[{"type": "list_files", "path": "SKILL.md"}]),
                   command("search", parsed=[{"type": "search", "path": "SKILL.md"}]),
                   output("a", "done")]
        stats = self.summary(records)["overall"]
        self.assertEqual(stats["recognized_skill_reads"], 2)
        self.assertEqual(stats["skill_reads_by_name"], {"nx-workspace": 2})

    def test_missing_edit_is_unknown_not_zero_and_failed_patch_is_not_boundary(self):
        records = [call("a", "read"), usage("1", 100, 100),
                   item("FileChange", "failed", status="failed"), output("a", "done")]
        stats = self.summary(records)
        self.assertIsNone(stats["first_recorded_edit"])
        self.assertIsNone(stats["before_first_edit"])
        self.assertIsNone(stats["context"]["checkpoints"]["before_first_edit"])
        self.assertEqual(stats["overall"]["file_change_events_by_status"], {"failed": 1})

    def test_duplicate_execution_id_is_rejected(self):
        records = [call("a", "read"), usage("1", 100, 100), command("a"), command("a")]
        with self.assertRaisesRegex(ValueError, "Duplicate execution"):
            self.summary(records)

    def test_overlapping_edit_calls_do_not_guess_a_boundary(self):
        records = [call("a", "edit"), call("b", "read"), usage("1", 100, 100),
                   item("FileChange", "patch", status="completed")]
        stats = self.summary(records)
        self.assertIsNone(stats["before_first_edit"])
        self.assertEqual(stats["first_recorded_edit"]["status"], "ambiguous enclosing tool call")

    def test_assessment_pass_fail_and_skip_counts_come_from_log_summaries(self):
        cases = [
            ("Ran 7 tests in 1.656s\n\nOK\n", "Tests 4 passed (4)\n", 0, 0, 0),
            ("Ran 7 tests in 1.656s\n\nFAILED (failures=1, errors=2, skipped=1)\n",
             "Tests 2 failed | 1 passed | 1 skipped (4)\n", 5, 2, 1),
            ("Ran 7 tests in 1.656s\n\nOK (skipped=1)\n", "Tests 4 passed (4)\n", 0, 1, 0),
        ]
        for cli, stream, failed, skipped, exit_code in cases:
            with self.subTest(cli=cli), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                (directory / "result.json").write_text(json.dumps({
                    "cli_exit_code": exit_code, "stream_exit_code": exit_code,
                }))
                (directory / "cli.log").write_text(cli)
                (directory / "stream.log").write_text(stream)
                result = assessment_statistics(directory)
                self.assertEqual(result["total"], 11)
                self.assertEqual(result["failed_or_error"], failed)
                self.assertEqual(result["skipped"], skipped)

    def test_incomplete_assessment_log_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "result.json").write_text('{"cli_exit_code":0,"stream_exit_code":0}')
            (directory / "cli.log").write_text("Ran 7 tests in 1s\nOK\n")
            (directory / "stream.log").write_text("Tests 3 passed (4)\n")
            with self.assertRaisesRegex(ValueError, "Incomplete Vitest"):
                assessment_statistics(directory)


if __name__ == "__main__":
    unittest.main()
