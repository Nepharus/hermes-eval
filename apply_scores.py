#!/usr/bin/env python3
"""
Write an outside judge's scores into history.db for a run made with
collect_responses.py, then write the usual results markdown.

scores.json: {"run_id": 19, "judge": "Claude (claude-opus-5-5)",
              "scores": {"1": {"score": 7, "reasoning": "..."}, ...}}

    python apply_scores.py scores_run19.json
"""
import json
import sys
from pathlib import Path

import evalcore as ec
from evalcore import Result


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    run_id = spec["run_id"]
    with ec.connect() as conn:
        profile, model, suite_version = conn.execute(
            "SELECT profile, model, suite_version FROM runs WHERE id=?", (run_id,)).fetchone()
        rows = conn.execute(
            "SELECT id, prompt_number, prompt_name, response, notes FROM results WHERE run_id=? "
            "ORDER BY prompt_number", (run_id,)).fetchall()
        results = []
        for rid, num, name, response, notes in rows:
            s = spec["scores"].get(str(num))
            score = s["score"] if s else None
            reasoning = s["reasoning"] if s else ""
            conn.execute("UPDATE results SET score=?, notes=?, judge_reasoning=? WHERE id=?",
                         (score, reasoning or notes, reasoning, rid))
            results.append(Result(num, name, score, response, reasoning or notes, reasoning))
    ec.complete_run(run_id, results, spec.get("notes", ""))
    out = ec.default_output_path(profile, run_id)
    ec.write_results_markdown(results, profile, model, suite_version, out, run_id, judge=spec["judge"])
    ec.print_summary(results, len(results))


if __name__ == "__main__":
    main()
