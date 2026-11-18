#!/usr/bin/env python3
"""
Automated evaluation runner with SQLite history and judge-model scoring.

Each prompt is sent to the profile under test with
`hermes -p <profile> chat --query-file - -Q`, and the response is scored by a
second `hermes` call to the judge profile, which must return JSON.
Run it from a normal shell. It doesn't need to run inside a Hermes session.

Examples:
    python run_suite.py init
    python run_suite.py run --profile homepc --judge-profile nvidia
    python run_suite.py run --profile nvidia --manual-score --prompts 1,3
    python run_suite.py history
    python run_suite.py compare 4 5
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import evalcore as ec
from evalcore import Result, TestPrompt

ANSWER_PREAMBLE = (
    "Answer the following prompt directly in your reply. Follow every constraint "
    "exactly. Put all output (including any code) in the reply itself. Do not "
    "create or edit files and do not use tools.\n\n"
)

JUDGE_PROMPT = """You are a strict expert evaluator. Score the model's response to the given prompt on a 1-10 scale.
Apply the scoring guide literally. Do not give credit for constraints the response only partly meets.

PROMPT:
{prompt}

SCORING GUIDE:
{scoring_guide}

RUBRIC:
10 = Exemplary: Perfect execution, nuanced, handles edge cases, shows insight
9  = Excellent: Fully correct, well-structured, minor polish only
8  = Strong: Correct, complete, minor omissions or awkward phrasing
7  = Good: Mostly correct, one notable gap or error
6  = Adequate: Core answer right, significant gaps or confusion
5  = Mediocre: Half-right, half-wrong; major gaps
4  = Weak: Missing key concepts, confused reasoning
3  = Poor: Mostly wrong, hallucinates, fails instruction
2  = Very Poor: Barely addresses prompt, incoherent
1  = Failure: Refuses, nonsense, or completely off-topic

Penalties:
-1 to -2: Not following format constraints, missing explicit requirements
-1: Verbosity when concise asked (or vice versa)
No half-points. Round down.

MODEL RESPONSE (between the markers):
<<<RESPONSE
{response}
RESPONSE>>>

Output ONLY a JSON object, with no code fences and no other text:
{{"score": <integer 1-10>, "reasoning": "<concise explanation citing specific evidence from the response>"}}"""

# Hermes prints startup/connection failures to stdout with exit code 0,
# so check the text as well as the return code.
HERMES_ERROR_PATTERNS = (
    "Hermes couldn't start",
    "Your message was not sent",
)


class HermesError(RuntimeError):
    pass


def ask_hermes(profile: str, query: str, timeout: int) -> str:
    """Send one query to a Hermes profile and return its final reply text."""
    # Run from an empty scratch dir so an agentic profile can't touch the eval dir.
    with tempfile.TemporaryDirectory(prefix="hermes-eval-") as scratch:
        try:
            proc = subprocess.run(
                ["hermes", "-p", profile, "chat", "--query-file", "-", "-Q",
                 "--source", "tool", "--in", scratch],
                input=query, capture_output=True, text=True, timeout=timeout,
                env=ec.hermes_env(), cwd=scratch,
            )
        except FileNotFoundError:
            raise HermesError("`hermes` not found on PATH")
        except subprocess.TimeoutExpired:
            raise HermesError(f"timed out after {timeout}s")
    out = proc.stdout.strip()
    if proc.returncode != 0:
        detail = (proc.stderr.strip() or out)[-500:]
        raise HermesError(f"exit code {proc.returncode}: {detail}")
    if not out:
        raise HermesError(f"empty reply. stderr: {proc.stderr.strip()[-500:]}")
    if any(pat in out[:300] for pat in HERMES_ERROR_PATTERNS):
        raise HermesError(out[:500])
    return out


def parse_judge_json(text: str) -> Tuple[int, str]:
    """Pull {"score": n, "reasoning": "..."} out of the judge's reply."""
    candidates = [text]
    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    # Last {...} that contains "score"
    for m in reversed(list(re.finditer(r'\{[^{}]*"score"[^{}]*\}', text, re.DOTALL))):
        candidates.append(m.group(0))

    for c in candidates:
        try:
            data = json.loads(c)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict) or "score" not in data:
            continue
        score = int(data["score"])
        if not 1 <= score <= 10:
            raise ValueError(f"judge score out of range: {score}")
        return score, str(data.get("reasoning", "")).strip()
    raise ValueError(f"no JSON score in judge reply: {text[:300]!r}")


def score_with_judge(judge_profile: str, prompt: TestPrompt, response: str,
                     timeout: int, retries: int = 1) -> Tuple[int, str]:
    """Score a response with the judge profile. Raises on failure."""
    query = JUDGE_PROMPT.format(prompt=prompt.prompt, scoring_guide=prompt.scoring_guide,
                                response=response)
    last_err = None
    for _ in range(retries + 1):
        try:
            return parse_judge_json(ask_hermes(judge_profile, query, timeout))
        except (HermesError, ValueError) as e:
            last_err = e
    raise RuntimeError(f"judge failed: {last_err}")


def manual_score(prompt: TestPrompt, response: str) -> Tuple[Optional[int], str]:
    print(f"\n--- RESPONSE ---\n{response}\n--- END RESPONSE ---")
    print(f"\nSCORING GUIDE:\n{prompt.scoring_guide}\n")
    score = ec.ask_score()
    if score is None:
        return None, "Not scored"
    return score, ec.ask_line("  Notes: ")


# =============================================================================
# Main Runner
# =============================================================================

def run_suite(profile: str, prompts: list, suite_version: str, judge_profile: Optional[str],
              timeout: int) -> Tuple[int, list]:
    """Send every prompt to the profile, score each reply, and record it in history.db."""
    model = ec.profile_model(profile)
    judge_model = ec.profile_model(judge_profile) if judge_profile else ""
    run_id = ec.create_run(profile, model, suite_version, source="auto",
                           judge_profile=judge_profile or "manual", judge_model=judge_model)
    ec.store_prompts(prompts, suite_version)
    interactive = sys.stdin.isatty()

    print(f"Run ID: {run_id}")
    print(f"Profile: {profile} ({model or 'model unknown'})")
    print(f"Judge: {judge_profile + f' ({judge_model})' if judge_profile else 'manual'}")
    print(f"Suite: {suite_version}, {len(prompts)} prompts")

    results = []
    errors = 0
    for prompt in prompts:
        print(f"\n[{prompt.number}] {prompt.name} -> {profile} ...", flush=True)
        try:
            response = ask_hermes(profile, ANSWER_PREAMBLE + prompt.prompt, timeout)
        except HermesError as e:
            errors += 1
            print(f"  ERROR: {e}")
            result = Result(prompt.number, prompt.name, None, "", f"ERROR: {e}")
            results.append(result)
            ec.save_result(run_id, result)
            continue
        print(f"  Got {len(response)} chars")

        if judge_profile:
            print(f"  Scoring with judge ({judge_profile}) ...", flush=True)
            try:
                score, reasoning = score_with_judge(judge_profile, prompt, response, timeout)
                notes = reasoning
                print(f"  Score: {score}/10 - {reasoning[:120]}")
            except RuntimeError as e:
                print(f"  {e}")
                if interactive:
                    print("  Falling back to manual scoring.")
                    score, notes = manual_score(prompt, response)
                    reasoning = f"JUDGE FAILED: {e}"
                else:
                    score, notes, reasoning = None, f"JUDGE FAILED: {e}", ""
        else:
            score, notes = manual_score(prompt, response)
            reasoning = ""

        result = Result(prompt.number, prompt.name, score, response, notes, reasoning)
        results.append(result)
        ec.save_result(run_id, result)

    run_notes = f"{errors} prompt(s) failed to get a response" if errors else ""
    ec.complete_run(run_id, results, run_notes)
    return run_id, results


def print_history(profile: Optional[str] = None, limit: int = 20):
    rows = ec.get_history(profile, limit)
    if not rows:
        print("No history found.")
        return

    print(f"\n{'ID':<4} {'Profile':<11} {'Model':<34} {'Suite':<6} {'Source':<7} {'Started':<17} {'Score'}")
    print("-" * 95)
    for run_id, prof, model, suite, source, started, completed, total, max_s in rows:
        if completed is None:
            score_str = "incomplete"
        else:
            score_str = f"{total}/{max_s}" if total is not None else "—"
        print(f"{run_id:<4} {prof:<11} {(model or '?')[:34]:<34} {(suite or '?'):<6} "
              f"{(source or '?'):<7} {(started or '')[:16]:<17} {score_str}")


def print_comparison(run_ids: list):
    runs = ec.get_runs(run_ids)
    if not runs:
        print("No data for those run IDs.")
        return
    found = [r[0] for r in runs]
    missing = sorted(set(run_ids) - set(found))
    if missing:
        print(f"Run(s) not found: {', '.join(map(str, missing))}")

    versions = {r[3] for r in runs}
    if len(versions) > 1:
        print(f"WARNING: these runs use different suite versions ({', '.join(sorted(v or '?' for v in versions))}); "
              "prompts may differ, so scores aren't directly comparable.")

    print()
    for run_id, prof, model, suite, started, total, max_s in runs:
        print(f"  #{run_id}: {prof} / {model or '?'} / suite {suite or '?'} / {(started or '')[:16]} "
              f"/ total {total if total is not None else '—'}/{max_s if max_s is not None else '—'}")

    col = 8
    print(f"\n{'Prompt':<30} " + " ".join(f"{'#' + str(i):>{col}}" for i in found))
    print("-" * (31 + (col + 1) * len(found)))
    for (num, name), by_run in ec.get_scores(found).items():
        cells = []
        for i in found:
            if i not in by_run:
                cells.append("n/a")      # prompt not in this run
            elif by_run[i] is None:
                cells.append("skip")     # prompt present but unscored
            else:
                cells.append(str(by_run[i]))
        print(f"{f'{num}. {name}'[:30]:<30} " + " ".join(f"{c:>{col}}" for c in cells))


# =============================================================================
# CLI
# =============================================================================

def main():
    profiles = ec.list_profiles()
    parser = argparse.ArgumentParser(description="Automated model evaluation suite with SQLite history")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run the evaluation suite against a profile")
    run_p.add_argument("--profile", required=True, choices=profiles)
    judge = run_p.add_mutually_exclusive_group()
    judge.add_argument("--judge-profile", choices=profiles, default="nvidia",
                       help="Profile that scores the responses (default: nvidia)")
    judge.add_argument("--manual-score", action="store_true", help="Score each response by hand")
    run_p.add_argument("--suite", default=str(ec.DEFAULT_SUITE))
    run_p.add_argument("--prompts", help="Only run these prompt numbers, e.g. 1,3,7")
    run_p.add_argument("--timeout", type=int, default=600, help="Seconds per hermes call (default 600)")
    run_p.add_argument("--output", help="Output markdown file (default: eval/results/...)")

    hist_p = subparsers.add_parser("history", help="Show run history")
    hist_p.add_argument("--profile", help="Filter by profile")
    hist_p.add_argument("--limit", type=int, default=20)

    cmp_p = subparsers.add_parser("compare", help="Compare specific runs")
    cmp_p.add_argument("run_ids", nargs="+", type=int, help="Run IDs to compare")

    subparsers.add_parser("init", help="Initialize / upgrade the database")

    args = parser.parse_args()
    ec.init_db()

    if args.command == "init":
        print(f"Database initialized at {ec.DB_PATH}")
    elif args.command == "history":
        print_history(args.profile, args.limit)
    elif args.command == "compare":
        print_comparison(args.run_ids)
    elif args.command == "run":
        suite_path = Path(args.suite).expanduser()
        if not suite_path.exists():
            ec.die(f"Suite not found: {suite_path}")
        suite_version = ec.parse_suite_version(suite_path)
        prompts = ec.select_prompts(ec.parse_suite(suite_path), args.prompts)
        if not prompts:
            ec.die("No prompts selected.")
        print(f"Loaded {len(prompts)} prompts from {suite_path}")

        judge_profile = None if args.manual_score else args.judge_profile
        if judge_profile == args.profile:
            print(f"Note: {args.profile} is judging its own answers; scores may be biased.")

        run_id, results = run_suite(args.profile, prompts, suite_version, judge_profile, args.timeout)

        output = Path(args.output).expanduser() if args.output else ec.default_output_path(args.profile, run_id)
        judge_desc = f"{judge_profile} ({ec.profile_model(judge_profile)})" if judge_profile else "manual"
        ec.write_results_markdown(results, args.profile, ec.profile_model(args.profile), suite_version,
                                  output, run_id, judge=judge_desc)
        ec.print_summary(results, len(prompts))


if __name__ == "__main__":
    main()
