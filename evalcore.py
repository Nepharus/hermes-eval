"""
Shared code for the eval runners: suite parsing, SQLite history, profile
lookup, multi-line input and results markdown.

Used by run_suite.py (automated) and eval_runner.py (manual).
"""
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

EVAL_DIR = Path(__file__).resolve().parent
HERMES_DIR = EVAL_DIR.parent
PROFILES_DIR = HERMES_DIR / "profiles"
RESULTS_DIR = EVAL_DIR / "results"
# HERMES_EVAL_DB lets tests point at a scratch database.
DB_PATH = Path(os.environ.get("HERMES_EVAL_DB", EVAL_DIR / "history.db")).expanduser()
DEFAULT_SUITE = EVAL_DIR / "suite_v1.2.md"

# Line that ends a multi-line paste in the manual runners.
END_SENTINEL = "END"


@dataclass
class TestPrompt:
    number: int
    name: str
    prompt: str
    scoring_guide: str


@dataclass
class Result:
    number: int
    name: str
    score: Optional[int]
    response: str
    notes: str = ""
    judge_reasoning: str = ""


# =============================================================================
# SQLite Database
# =============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile TEXT NOT NULL,
    model TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_score INTEGER,
    max_score INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    prompt_number INTEGER NOT NULL,
    prompt_name TEXT NOT NULL,
    score INTEGER,
    response TEXT NOT NULL,
    notes TEXT,
    judge_reasoning TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompts (
    number INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    scoring_guide TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_prompt ON results(prompt_number);
CREATE INDEX IF NOT EXISTS idx_runs_profile ON runs(profile);
"""

# Columns added after v1. Added in place so existing history.db files upgrade.
MIGRATIONS = {
    "runs": {
        "suite_version": "TEXT",   # e.g. "v1", "v1.1" - don't compare across versions
        "source": "TEXT",          # "auto", "manual" or "legacy"
        "judge_profile": "TEXT",
        "judge_model": "TEXT",
    },
    "prompts": {
        "suite_version": "TEXT",
    },
}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the history DB, commit on success, and always close."""
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for col, coltype in cols.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def store_prompts(prompts: List[TestPrompt], suite_version: str):
    with connect() as conn:
        for p in prompts:
            conn.execute(
                """INSERT OR REPLACE INTO prompts (number, name, prompt, scoring_guide, suite_version)
                   VALUES (?, ?, ?, ?, ?)""",
                (p.number, p.name, p.prompt, p.scoring_guide, suite_version)
            )


def create_run(profile: str, model: str, suite_version: str, source: str,
               judge_profile: str = "", judge_model: str = "") -> int:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO runs (profile, model, started_at, notes, suite_version, source,
                                 judge_profile, judge_model)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (profile, model, datetime.now().isoformat(), "", suite_version, source,
             judge_profile, judge_model)
        )
        return cur.lastrowid


def complete_run(run_id: int, results: List[Result], notes: str = ""):
    scored = [r for r in results if r.score is not None]
    with connect() as conn:
        conn.execute(
            "UPDATE runs SET completed_at=?, total_score=?, max_score=?, notes=? WHERE id=?",
            (datetime.now().isoformat(), sum(r.score for r in scored), 10 * len(scored),
             notes, run_id)
        )


def save_result(run_id: int, result: Result):
    with connect() as conn:
        conn.execute(
            """INSERT INTO results (run_id, prompt_number, prompt_name, score, response, notes, judge_reasoning, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, result.number, result.name, result.score, result.response,
             result.notes, result.judge_reasoning, datetime.now().isoformat())
        )


def get_history(profile: Optional[str] = None, limit: int = 20):
    query = """SELECT id, profile, model, suite_version, source, started_at, completed_at,
                      total_score, max_score
               FROM runs {where} ORDER BY started_at DESC LIMIT ?"""
    with connect() as conn:
        if profile:
            return conn.execute(query.format(where="WHERE profile=?"), (profile, limit)).fetchall()
        return conn.execute(query.format(where=""), (limit,)).fetchall()


def get_runs(run_ids: List[int]):
    placeholders = ",".join("?" * len(run_ids))
    with connect() as conn:
        return conn.execute(
            f"""SELECT id, profile, model, suite_version, started_at, total_score, max_score
                FROM runs WHERE id IN ({placeholders}) ORDER BY id""",
            run_ids
        ).fetchall()


def get_scores(run_ids: List[int]):
    """Return {(prompt_number, prompt_name): {run_id: score_or_None}}."""
    placeholders = ",".join("?" * len(run_ids))
    with connect() as conn:
        rows = conn.execute(
            f"""SELECT prompt_number, prompt_name, run_id, score FROM results
                WHERE run_id IN ({placeholders}) ORDER BY prompt_number, run_id""",
            run_ids
        ).fetchall()
    table = {}
    for num, name, run_id, score in rows:
        table.setdefault((num, name), {})[run_id] = score
    return table


# =============================================================================
# Suite Parsing
# =============================================================================

def parse_suite_version(suite_path: Path) -> str:
    first_line = suite_path.read_text().splitlines()[0] if suite_path.exists() else ""
    m = re.search(r'\bv(\d+(?:\.\d+)*)\b', first_line)
    if m:
        return f"v{m.group(1)}"
    m = re.search(r'_v(\d+(?:\.\d+)*)\.md$', suite_path.name)
    return f"v{m.group(1)}" if m else suite_path.stem


def parse_suite(suite_path: Path) -> List[TestPrompt]:
    content = suite_path.read_text()
    prompts = []

    # Split by "### N. " pattern
    sections = re.split(r'\n### (\d+)\.\s+(.+?)\n', content)

    for i in range(1, len(sections), 3):
        num = int(sections[i])
        name = sections[i + 1].strip()
        body = sections[i + 2] if i + 2 < len(sections) else ""

        # Prompt runs from **Prompt:** to **Target capabilities:** (may include code blocks)
        prompt_match = re.search(r'\*\*Prompt:\*\*\n(.+?)\n\n\*\*Target capabilities:\*\*', body, re.DOTALL)
        prompt = ""
        if prompt_match:
            # Strip markdown blockquote markers but keep code blocks as-is
            prompt = re.sub(r'^> ?', '', prompt_match.group(1), flags=re.MULTILINE).strip()

        scoring_match = re.search(r'\*\*Scoring guide:\*\*\n(.+?)(?:\n\n---|\n\n###|$)', body, re.DOTALL)
        scoring = scoring_match.group(1).strip() if scoring_match else ""

        if prompt:
            prompts.append(TestPrompt(num, name, prompt, scoring))

    return prompts


def select_prompts(prompts: List[TestPrompt], only: Optional[str]) -> List[TestPrompt]:
    """Filter by a comma-separated list of prompt numbers, e.g. "1,3,7"."""
    if not only:
        return prompts
    wanted = {int(n) for n in only.split(",") if n.strip()}
    return [p for p in prompts if p.number in wanted]


# =============================================================================
# Hermes profiles
# =============================================================================

def list_profiles() -> List[str]:
    if not PROFILES_DIR.is_dir():
        return []
    return sorted(p.name for p in PROFILES_DIR.iterdir() if (p / "config.yaml").exists())


def profile_model(profile: str) -> str:
    """Read model.default from the profile's config.yaml ("" if unknown)."""
    config = PROFILES_DIR / profile / "config.yaml"
    if not config.exists():
        return ""
    text = config.read_text()
    try:
        import yaml
        model = (yaml.safe_load(text) or {}).get("model")
        if isinstance(model, dict):
            return str(model.get("default") or model.get("model") or "")
        return str(model or "")
    except Exception:
        # Fallback: first "default:" inside the top-level "model:" block
        m = re.search(r'^model:\s*\n((?:[ \t]+.*\n|\s*\n)+)', text, re.MULTILINE)
        if m:
            d = re.search(r'^\s+(?:default|model):\s*["\']?([^"\'\n#]+)', m.group(1), re.MULTILINE)
            if d:
                return d.group(1).strip()
    return ""


# =============================================================================
# Input / output
# =============================================================================

def read_response(label: str = "response") -> Optional[str]:
    """
    Read a multi-line response from stdin.

    Paste the text, then type END on its own line (or press Ctrl-D).
    Typing SKIP as the first line skips the prompt. Typing @path loads the
    response from a file. Returns None for SKIP.
    """
    print(f"Paste the {label}, then type {END_SENTINEL} on its own line "
          f"(or Ctrl-D). SKIP to skip, @path to load from a file.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == END_SENTINEL:
            break
        if not lines:
            if line.strip().upper() == "SKIP":
                return None
            if line.strip().startswith("@"):
                return Path(line.strip()[1:]).expanduser().read_text().strip()
        lines.append(line)
    return "\n".join(lines).strip() or None   # empty paste counts as SKIP


def ask_score(prompt_text: str = "Score 1-10 (Enter=skip): ") -> Optional[int]:
    while True:
        try:
            s = input(prompt_text).strip()
        except EOFError:
            return None
        if not s:
            return None
        if s.isdigit() and 1 <= int(s) <= 10:
            return int(s)
        print("  Enter 1-10 or blank to skip")


def ask_line(prompt_text: str) -> str:
    try:
        return input(prompt_text).strip()
    except EOFError:
        return ""


def default_output_path(profile: str, run_id: int) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR / f"results_{profile}_run{run_id}_{datetime.now().strftime('%Y%m%d')}.md"


def write_results_markdown(results: List[Result], profile: str, model: str, suite_version: str,
                           output_path: Path, run_id: int, judge: str = ""):
    total = sum(r.score for r in results if r.score is not None)
    max_possible = 10 * len([r for r in results if r.score is not None])

    lines = [
        f"# Eval Results: Run #{run_id} | {profile} | {model or 'unknown model'} | "
        f"suite {suite_version} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if judge:
        lines += [f"Judge: {judge}", ""]
    lines += [
        "| # | Prompt | Score | Notes |",
        "|---|--------|-------|-------|",
    ]

    for r in results:
        score_str = f"{r.score}/10" if r.score is not None else "—"
        notes = r.notes.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r.number} | {r.name} | {score_str} | {notes} |")

    lines.extend([
        f"| **Total** | | **{total}/{max_possible}** | |",
        "",
        "## Responses",
    ])
    for r in results:
        lines += ["", f"### {r.number}. {r.name}", "", r.response or "_(no response)_"]
        if r.judge_reasoning:
            lines += ["", f"**Judge:** {r.judge_reasoning}"]

    lines.extend([
        "",
        "## Observations",
        "- Strengths:",
        "- Weaknesses:",
        "- Notable failures:",
        "- Compared to previous run:",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    print(f"\nResults written to {output_path}")


def print_summary(results: List[Result], n_prompts: int):
    scored = [r for r in results if r.score is not None]
    if not scored:
        print("\nNo prompts were scored.")
        return
    total = sum(r.score for r in scored)
    print("\n=== SUMMARY ===")
    print(f"Scored: {len(scored)}/{n_prompts}")
    print(f"Average: {total / len(scored):.1f}/10")
    print(f"Total: {total}/{10 * len(scored)}")


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def hermes_env() -> dict:
    """
    Environment for `hermes` subprocesses. If HOME doesn't point at the
    directory that holds this .hermes (e.g. when run from a sandboxed agent),
    point HOME at it so `hermes -p <profile>` finds the profiles.
    """
    env = dict(os.environ)
    if Path(env.get("HOME", "")).expanduser().resolve() / ".hermes" != HERMES_DIR:
        env["HOME"] = str(HERMES_DIR.parent)
    return env
