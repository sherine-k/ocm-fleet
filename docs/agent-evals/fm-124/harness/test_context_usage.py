"""Telemetry contract tests; no model calls or external I/O."""
import unittest

from context_usage import analyze, checkpoint_summary


def record(kind, payload):
    return {"type": kind, "timestamp": "2026-10-23T12:00:00Z", "payload": payload}


def usage(response, tokens, cumulative):
    return record("token_usage_record", {
        "response_id": response,
        "usage": dict(input_tokens=tokens, cached_input_tokens=0,
                      output_tokens=1, reasoning_output_tokens=0),
        "thread_token_usage": dict(input_tokens=cumulative,
                                   cached_input_tokens=0, output_tokens=int(response),
                                   reasoning_output_tokens=0),
    })


def call(identifier, code):
    return record("response_item", {"type": "custom_tool_call", "name": "exec",
                                    "call_id": identifier, "input": code})


def output(identifier, text):
    return record("response_item", {
        "type": "custom_tool_call_output", "call_id": identifier,
        "output": [{"type": "input_text", "text": text}],
    })


class ContextUsageTests(unittest.TestCase):
    def test_result_enters_next_request_and_counts_visible_text_bytes(self):
        result = analyze([
            call("read", 'cat .agents/skills/nx-workspace/SKILL.md'),
            usage("1", 100, 100),
            output("read", "é"),
            call("edit", 'await tools.apply_patch("patch")'),
            usage("2", 150, 250),
        ], "control")
        first, second = result["requests"]
        self.assertEqual(first["included_tool_results"], [])
        self.assertEqual(second["included_tool_results"], ["read"])
        self.assertEqual(second["input_delta"], 50)
        self.assertEqual(result["tool_results"][0]["first_included_request"], 2)
        self.assertEqual(result["tool_results"][0]["visible_text_bytes"], 2)
        self.assertEqual(result["tool_results"][0]["guidance_path_mentions"],
                         [".agents/skills/nx-workspace/SKILL.md"])
        self.assertIn("first apply_patch request", second["checkpoints"])

    def test_treatment_can_finish_without_reading_a_skill_or_editing(self):
        result = analyze([usage("1", 100, 100)], "treatment")
        self.assertEqual(result["totals"]["input_tokens"], 100)
        self.assertEqual(result["tool_results"], [])

    def test_batched_results_are_linked_without_allocating_token_delta(self):
        result = analyze([
            call("a", "cat AGENTS.md"), call("b", "cat source.ts"),
            usage("1", 100, 100), output("a", "guide"), output("b", "code"),
            usage("2", 170, 270),
        ], "control")
        self.assertEqual(result["requests"][1]["included_tool_results"], ["a", "b"])
        self.assertTrue(all("input_tokens" not in item for item in result["tool_results"]))

    def test_compaction_and_negative_delta_are_preserved(self):
        result = analyze([
            usage("1", 100, 100), record("compacted", {}), usage("2", 60, 160),
        ], "control")
        self.assertEqual(result["requests"][1]["input_delta"], -40)
        self.assertEqual(result["compactions_observed"], 1)

    def test_usage_integrity_failures_are_rejected(self):
        for records in ([usage("1", 100, 101)],
                        [usage("1", 100, 100), usage("1", 100, 200)]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                analyze(records, "control")

    def test_unconsumed_final_tool_output_has_no_included_request(self):
        result = analyze([
            call("read", "cat AGENTS.md"), usage("1", 100, 100), output("read", "guide"),
        ], "control")
        self.assertIsNone(result["tool_results"][0]["first_included_request"])


class CheckpointSummaryTests(unittest.TestCase):
    def analysis(self):
        return analyze([
            call("read", "cat .agents/skills/nx-workspace/SKILL.md"),
            usage("1", 100, 100), output("read", "skill body"),
            call("edit", 'await tools.apply_patch("patch")'), usage("2", 150, 250),
            output("edit", "done"), call("later", "cat docs/ui/AGENTS.md"),
            usage("3", 180, 430), output("later", "later guide"),
            usage("4", 200, 630),
        ], "control")

    def test_two_checkpoints_and_confirmed_reads_before_reviewed_edit(self):
        summary = checkpoint_summary(self.analysis(), {
            "first_edit_request": 2,
            "guidance_reads": [
                {"source": ".agents/skills/nx-workspace/SKILL.md", "call_id": "read"},
                {"source": "docs/ui/AGENTS.md", "call_id": "later"},
            ],
        })
        self.assertEqual(set(summary["checkpoints"]), {"initial_request", "before_first_edit"})
        self.assertEqual(summary["checkpoints"]["initial_request"]["input_tokens"], 100)
        self.assertEqual(summary["checkpoints"]["before_first_edit"]["input_tokens"], 150)
        self.assertEqual(summary["input_growth_before_first_edit"], 50)
        self.assertEqual(summary["guidance_reads_before_first_edit"], [{
            "source": ".agents/skills/nx-workspace/SKILL.md", "call_id": "read",
            "first_included_request": 2,
        }])
        self.assertEqual(summary["first_edit_status"], "reviewed")
        self.assertEqual(summary["total_input_plus_output_tokens"], 634)

    def test_patch_mention_is_only_a_candidate_and_not_a_confirmed_read(self):
        summary = checkpoint_summary(self.analysis())
        self.assertEqual(summary["first_edit_status"], "unreviewed apply_patch candidate")
        self.assertIsNone(summary["guidance_reads_before_first_edit"])

    def test_review_can_identify_an_earlier_shell_edit(self):
        summary = checkpoint_summary(self.analysis(), {
            "first_edit_request": 1, "guidance_reads": [],
        })
        self.assertEqual(summary["checkpoints"]["before_first_edit"]["request_number"], 1)
        self.assertEqual(summary["guidance_reads_before_first_edit"], [])

    def test_reviewed_no_edit_is_distinct_from_unreviewed_missing_edit(self):
        analysis = analyze([usage("1", 100, 100)], "control")
        missing = checkpoint_summary(analysis)
        reviewed = checkpoint_summary(analysis, {
            "first_edit_request": None, "guidance_reads": [],
        })
        self.assertEqual(missing["first_edit_status"], "unreviewed; no apply_patch found")
        self.assertEqual(reviewed["first_edit_status"], "reviewed; no edit")
        self.assertIsNone(reviewed["checkpoints"]["before_first_edit"])
        self.assertIsNone(reviewed["input_growth_before_first_edit"])

    def test_unknown_read_call_and_invalid_request_are_rejected(self):
        for review in (
            {"first_edit_request": 99, "guidance_reads": []},
            {"first_edit_request": 2, "guidance_reads": [{"source": "guide", "call_id": "missing"}]},
        ):
            with self.subTest(review=review), self.assertRaises(ValueError):
                checkpoint_summary(self.analysis(), review)


if __name__ == "__main__":
    unittest.main()
