#!/usr/bin/env python3
"""
Clean up history.db: drop runs that aren't usable for v1.2 comparisons.

A run is dropped if any of these are true:
  - its suite_version isn't v1.2 (v1, v1.1, legacy imports)
  - it has fewer results than the suite has prompts (aborted or --prompts test runs)
  - it never completed, UNLESS it's a pending outside-judge run
    (every response collected, nothing scored yet) that apply_scores.py can still finish

Shows what it would delete by default. Add --apply to delete. A timestamped
backup of the database is made before anything is deleted.

    python cleanup_history.py
    python cleanup_history.py --apply
    python cleanup_history.py --apply --drop-pending
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

KEEP_VERSION = "v1.2"
SUITE_PROMPTS = 8


def classify(conn, drop_pending):
    runs = conn.execute(
        """SELECT r.id, r.profile, r.model, r.suite_version, r.completed_at,
                  r.total_score, r.max_score, r.judge_profile,
                  COUNT(x.id),
                  SUM(CASE WHEN x.response <> '' THEN 1 ELSE 0 END),
                  SUM(CASE WHEN x.score IS NOT NULL THEN 1 ELSE 0 END)
           FROM runs r LEFT JOIN results x ON x.run_id = r.id
           GROUP BY r.id ORDER BY r.id"""
    ).fetchall()

    drop, keep = [], []
    for (rid, profile, model, version, completed, total, max_s, judge,
         n_results, n_responses, n_scored) in runs:
        n_responses = n_responses or 0
        n_scored = n_scored or 0
        pending = (completed is None and n_results == SUITE_PROMPTS
                   and n_responses == SUITE_PROMPTS and n_scored == 0)

        if version != KEEP_VERSION:
            reason = f"suite {version or '?'}"
        elif n_results < SUITE_PROMPTS:
            reason = f"partial ({n_results}/{SUITE_PROMPTS} results)"
        elif completed is None and not pending:
            reason = "never completed"
        elif pending and drop_pending:
            reason = "pending outside-judge run (--drop-pending)"
        else:
            reason = None

        score = f"{total}/{max_s}" if total is not None else ("pending" if pending else "-")
        row = (rid, profile, model or "?", version or "?", judge or "?", score, reason)
        (drop if reason else keep).append(row)
    return drop, keep


def show(title, rows, with_reason):
    print(f"\n{title} ({len(rows)})")
    print(f"  {'ID':<4} {'Profile':<11} {'Model':<36} {'Suite':<6} {'Judge':<11} {'Score':<8}"
          + (" Reason" if with_reason else ""))
    for rid, profile, model, version, judge, score, reason in rows:
        print(f"  {rid:<4} {profile:<11} {model[:36]:<36} {version:<6} {judge[:11]:<11} {score:<8}"
              + (f" {reason}" if with_reason else ""))


def main():
    parser = argparse.ArgumentParser(description="Remove old, partial and abandoned runs from history.db")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent / "history.db"),
                        help="Path to history.db (default: next to this script)")
    parser.add_argument("--apply", action="store_true", help="Delete the runs (default: preview only)")
    parser.add_argument("--drop-pending", action="store_true",
                        help="Also drop pending outside-judge runs that haven't been scored yet")
    args = parser.parse_args()

    db = Path(args.db).expanduser()
    if not db.exists():
        sys.exit(f"Database not found: {db}")

    conn = sqlite3.connect(db)
    drop, keep = classify(conn, args.drop_pending)
    show("Drop", drop, with_reason=True)
    show("Keep", keep, with_reason=False)

    if not drop:
        print("\nNothing to delete.")
        return
    if not args.apply:
        print("\nPreview only. Run again with --apply to delete these runs.")
        return

    conn.close()
    backup = db.with_name(f"{db.stem}.backup_{datetime.now():%Y%m%d_%H%M%S}{db.suffix}")
    shutil.copy2(db, backup)
    print(f"\nBackup: {backup}")

    ids = [r[0] for r in drop]
    marks = ",".join("?" * len(ids))
    conn = sqlite3.connect(db)
    with conn:
        n_res = conn.execute(f"DELETE FROM results WHERE run_id IN ({marks})", ids).rowcount
        n_run = conn.execute(f"DELETE FROM runs WHERE id IN ({marks})", ids).rowcount
        n_pr = conn.execute("DELETE FROM prompts WHERE suite_version IS NOT ?", (KEEP_VERSION,)).rowcount
    conn.execute("VACUUM")
    conn.close()
    print(f"Deleted {n_run} runs, {n_res} results, {n_pr} non-{KEEP_VERSION} prompt rows.")


if __name__ == "__main__":
    main()
