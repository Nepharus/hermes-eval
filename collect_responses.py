#!/usr/bin/env python3
"""
Collect responses from a profile without judging them, so an outside judge
(e.g. Claude) can score them afterwards with apply_scores.py.

Creates a run in history.db with every score left NULL and writes the raw
responses to results/pending_<profile>_run<id>.json.

    python collect_responses.py --profile nvidia --judge-label claude --judge-model claude-opus-5-5
"""
import argparse
import json
from pathlib import Path

import evalcore as ec
from evalcore import Result
from run_suite import ANSWER_PREAMBLE, HermesError, ask_hermes


def main():
    parser = argparse.ArgumentParser(description="Collect unjudged responses from a profile")
    parser.add_argument("--profile", required=True, choices=ec.list_profiles())
    parser.add_argument("--suite", default=str(ec.DEFAULT_SUITE))
    parser.add_argument("--prompts", help="Only run these prompt numbers, e.g. 1,3,7")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--judge-label", default="external")
    parser.add_argument("--judge-model", default="")
    args = parser.parse_args()

    ec.init_db()
    suite_path = Path(args.suite).expanduser()
    suite_version = ec.parse_suite_version(suite_path)
    prompts = ec.select_prompts(ec.parse_suite(suite_path), args.prompts)
    model = ec.profile_model(args.profile)
    run_id = ec.create_run(args.profile, model, suite_version, source="auto",
                           judge_profile=args.judge_label, judge_model=args.judge_model)
    ec.store_prompts(prompts, suite_version)
    print(f"Run ID: {run_id}  Profile: {args.profile} ({model})  Suite: {suite_version}", flush=True)

    out_path = ec.RESULTS_DIR / f"pending_{args.profile}_run{run_id}.json"
    pending = {"run_id": run_id, "profile": args.profile, "model": model,
               "suite_version": suite_version, "responses": []}
    for prompt in prompts:
        print(f"[{prompt.number}] {prompt.name} -> {args.profile} ...", flush=True)
        try:
            response, error = ask_hermes(args.profile, ANSWER_PREAMBLE + prompt.prompt, args.timeout), ""
            print(f"  Got {len(response)} chars", flush=True)
        except HermesError as e:
            response, error = "", f"ERROR: {e}"
            print(f"  {error}", flush=True)
        ec.save_result(run_id, Result(prompt.number, prompt.name, None, response, error))
        pending["responses"].append({"number": prompt.number, "name": prompt.name,
                                     "response": response, "error": error})
        out_path.write_text(json.dumps(pending, indent=2))
    print(f"Done. Responses in {out_path}", flush=True)


if __name__ == "__main__":
    main()
