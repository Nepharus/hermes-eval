#!/usr/bin/env python3
"""
Model Evaluation Suite Runner - manual version with SQLite history.

Prints each prompt. You run it on the model yourself, paste the full response
(multi-line is fine: finish with END on its own line or Ctrl-D, or give
@path/to/file), then score it. For the automated version, use run_suite.py.
"""
import argparse
from pathlib import Path

import evalcore as ec
from evalcore import Result


def main():
    profiles = ec.list_profiles()
    parser = argparse.ArgumentParser(description="Run model evaluation suite (manual)")
    parser.add_argument("--profile", required=True, choices=profiles,
                        help="Profile being tested (for history)")
    parser.add_argument("--model", help="Model name to record (default: read from the profile config)")
    parser.add_argument("--suite", default=str(ec.DEFAULT_SUITE),
                        help="Path to suite markdown file")
    parser.add_argument("--prompts", help="Only run these prompt numbers, e.g. 1,3,7")
    parser.add_argument("--output", help="Output markdown file (default: eval/results/...)")
    args = parser.parse_args()

    suite_path = Path(args.suite).expanduser()
    if not suite_path.exists():
        ec.die(f"Suite not found: {suite_path}")

    ec.init_db()
    suite_version = ec.parse_suite_version(suite_path)
    prompts = ec.select_prompts(ec.parse_suite(suite_path), args.prompts)
    if not prompts:
        ec.die("No prompts selected.")
    model = args.model or ec.profile_model(args.profile)
    print(f"Loaded {len(prompts)} prompts from {suite_path} (suite {suite_version})")

    run_id = ec.create_run(args.profile, model, suite_version, source="manual", judge_profile="manual")
    ec.store_prompts(prompts, suite_version)
    print(f"Run ID: {run_id}  Profile: {args.profile}  Model: {model or 'unknown'}")

    results = []
    for prompt in prompts:
        print(f"\n{'='*60}")
        print(f"PROMPT {prompt.number}: {prompt.name}")
        print(f"{'='*60}")
        print(f"\n{prompt.prompt}")
        print(f"\n>>> RUN THIS PROMPT VIA YOUR MODEL <<<\n")

        response = ec.read_response()
        if response is None:
            result = Result(prompt.number, prompt.name, None, "", "Skipped")
        else:
            print(f"\nSCORING GUIDE:\n{prompt.scoring_guide}")
            print("\nRUBRIC: 10=Exemplary ... 1=Failure (see suite file)")
            score = ec.ask_score("\nScore (1-10, Enter=skip): ")
            notes = ec.ask_line("Notes (optional): ") if score is not None else "Not scored"
            result = Result(prompt.number, prompt.name, score, response, notes)
        results.append(result)
        ec.save_result(run_id, result)

    ec.complete_run(run_id, results)
    output_path = Path(args.output).expanduser() if args.output else ec.default_output_path(args.profile, run_id)
    ec.write_results_markdown(results, args.profile, model, suite_version, output_path, run_id, judge="manual")
    ec.print_summary(results, len(prompts))


if __name__ == "__main__":
    main()
