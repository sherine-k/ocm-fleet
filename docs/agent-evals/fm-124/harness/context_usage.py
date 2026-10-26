"""Report initial and before-first-edit context from Codex 0.164 rollouts.

Provider usage is measured per request. Tool text is measured in UTF-8 bytes;
no request delta is allocated to a particular file or tool result. The full
timeline remains supporting evidence for the two-checkpoint summary.
"""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re


METRICS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def text_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(text_content(item) for item in value)
    if isinstance(value, dict):
        return value.get("text", "")
    return ""


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def analyze(records, run):
    requests, calls, results, pending, issued = [], {}, [], [], []
    response_ids = set()
    first_patch = False
    compactions = 0
    final_usage = None
    started = None
    for record in records:
        timestamp = datetime.datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        if started is None:
            started = timestamp
        payload = record.get("payload", {})
        if record["type"] == "compacted":
            compactions += 1
        if record["type"] == "response_item":
            kind = payload.get("type")
            if kind in ("custom_tool_call", "function_call"):
                identifier = payload["call_id"]
                if identifier in calls:
                    raise ValueError(f"Duplicate tool call: {identifier}")
                code = payload.get("input", payload.get("arguments", ""))
                calls[identifier] = {
                    "call_id": identifier, "tool_name": payload["name"],
                    "input_sha256": digest(code),
                    "guidance_path_mentions": sorted(set(re.findall(
                        r"(?:[~./\w-]+/)?(?:AGENTS|SKILL)\.md\b", code))),
                    "apply_patch_mention": payload["name"] == "apply_patch" or "tools.apply_patch(" in code,
                    "issued_request": None,
                }
                issued.append(identifier)
            elif kind in ("custom_tool_call_output", "function_call_output"):
                identifier = payload["call_id"]
                if identifier not in calls:
                    raise ValueError(f"Tool result without call: {identifier}")
                visible = text_content(payload.get("output", ""))
                item = {
                    **calls[identifier], "completed_at": record["timestamp"],
                    "visible_text_bytes": len(visible.encode("utf-8")),
                    "visible_text_sha256": digest(visible),
                    "first_included_request": None,
                }
                results.append(item)
                pending.append(item)
        if record["type"] != "token_usage_record":
            continue
        response_id = payload["response_id"]
        if response_id in response_ids:
            raise ValueError(f"Duplicate usage response: {response_id}")
        response_ids.add(response_id)
        number = len(requests) + 1
        usage = payload["usage"]
        marks = ["initial request"] if not requests else []
        if not first_patch and any(calls[key]["apply_patch_mention"] for key in issued):
            first_patch = True
            marks.append("first apply_patch request")
        for identifier in issued:
            calls[identifier]["issued_request"] = number
        for item in pending:
            item["first_included_request"] = number
        row = {
            "run": run, "request_number": number, "response_id": response_id,
            "response_completed_at": record["timestamp"],
            "seconds_until_usage_report": round((timestamp - started).total_seconds(), 3),
            **{key: usage[key] for key in METRICS},
            "input_delta": usage["input_tokens"] - requests[-1]["input_tokens"] if requests else 0,
            "input_growth_from_initial": usage["input_tokens"] - requests[0]["input_tokens"] if requests else 0,
            "included_tool_results": [item["call_id"] for item in pending],
            "issued_tool_calls": issued,
            "checkpoints": marks,
        }
        requests.append(row)
        pending, issued = [], []
        final_usage = payload["thread_token_usage"]
    if not requests:
        raise ValueError("No per-response usage records")
    totals = {key: sum(row[key] for row in requests) for key in METRICS}
    for key, value in totals.items():
        if value != final_usage[key]:
            raise ValueError(f"Usage sum mismatch for {key}: {value} != {final_usage[key]}")
    return {
        "run": run, "totals": totals, "compactions_observed": compactions,
        "requests": requests, "tool_calls": list(calls.values()), "tool_results": results,
        "attribution": "Path mentions are retrieval candidates, not confirmed reads. Bytes are not tokens. Request deltas include all history changes.",
    }


def checkpoint_summary(analysis, review=None):
    """Use reviewed edits/reads when supplied; never treat path mentions as reads.

    A reviewer checks the raw transcript for earlier shell edits and actual
    returned guidance content. Without that review, apply_patch is a candidate.
    The checkpoint uses input to the request issuing the edit, before the edit
    executes; the generated patch itself is output, not part of this input.
    """
    requests = {row["request_number"]: row for row in analysis["requests"]}
    initial = analysis["requests"][0]
    if review is None:
        edit = next((row for row in analysis["requests"]
                     if "first apply_patch request" in row["checkpoints"]), None)
        status = "unreviewed apply_patch candidate" if edit else "unreviewed; no apply_patch found"
    else:
        number = review["first_edit_request"]
        if number is not None and number not in requests:
            raise ValueError(f"Unknown first-edit request: {number}")
        edit = requests.get(number)
        status = "reviewed" if edit else "reviewed; no edit"
    reads = None
    if review is not None:
        results = {item["call_id"]: item for item in analysis["tool_results"]}
        reads = [] if edit else None
        for read in review["guidance_reads"]:
            if read["call_id"] not in results:
                raise ValueError(f"Unknown guidance-result call: {read['call_id']}")
            number = results[read["call_id"]]["first_included_request"]
            if edit and number is not None and number <= edit["request_number"]:
                reads.append({**read, "first_included_request": number})

    def checkpoint(row):
        return None if row is None else {
            key: row[key] for key in ("request_number", "input_tokens", "cached_input_tokens")
        }

    totals = analysis["totals"]
    return {
        "run": analysis["run"],
        "checkpoints": {"initial_request": checkpoint(initial), "before_first_edit": checkpoint(edit)},
        "first_edit_status": status,
        "input_growth_before_first_edit": edit["input_tokens"] - initial["input_tokens"] if edit else None,
        "guidance_reads_before_first_edit": reads,
        "totals": totals,
        "total_input_plus_output_tokens": totals["input_tokens"] + totals["output_tokens"],
        "requests": len(requests), "compactions_observed": analysis["compactions_observed"],
        "measurement_note": "Initial input includes all stock context and the task. Growth also includes source, tool results, and assistant history; it is not isolated guidance cost. Cached input is included in input; reasoning is included in output.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollout", type=Path)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, help="Reviewed first-edit request and confirmed guidance reads")
    args = parser.parse_args()
    with args.rollout.open() as source:
        result = analyze((json.loads(line) for line in source), args.run)
    args.output.mkdir(parents=True, exist_ok=True)
    review = json.loads(args.review.read_text()) if args.review else None
    summary = checkpoint_summary(result, review)
    (args.output / "checkpoints.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "context-usage.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / "context-usage.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(result["requests"][0]), lineterminator="\n")
        writer.writeheader()
        for row in result["requests"]:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value
                             for key, value in row.items()})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
