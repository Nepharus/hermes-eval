# Hermes eval suite

A small benchmark for comparing the models behind different
Hermes profiles. It sends a fixed set of prompts to a
profile, scores each reply from 1 to 10, keeps every run in a local SQLite
database, and writes a Markdown report per run, so you can track and compare
models over time.

Scoring can come from three places:

- **A judge profile.** A second Hermes profile grades each reply against the
  prompt's scoring guide and returns JSON (`run_suite.py`).
- **You, by hand.** The runner shows each reply and its scoring guide and asks
  for a score (`run_suite.py --manual-score`, or `eval_runner.py` when you run
  the prompts yourself).
- **An outside judge** such as Claude. Collect the replies first, score them
  elsewhere, then load the scores back in (`collect_responses.py` and
  `apply_scores.py`).

## Requirements

- Python 3.8+. PyYAML is optional: with it, the model name is read from each
  profile's `config.yaml`, and without it a simple fallback parser is used.
- The `hermes` CLI on your `PATH`.
- Hermes profiles in `~/.hermes/profiles/<name>/config.yaml`. This repo must sit
  at `~/.hermes/eval`, because the scripts find the profiles in the directory
  above it. The `--profile` options only accept profiles found there.

## The suites

Each suite is a Markdown file with eight prompts. Every prompt has a scoring
guide, and the maximum is 80 points.

| File | Version | Notes |
|------|---------|-------|
| `archive/suite_v1.md` | v1 | Original smoke test |
| `archive/suite_v1.1.md` | v1.1 | Revised smoke test. Too easy: a 12B model scored 79/80 |
| `suite_v1.2.md` | v1.2 | **Default.** Harder, and every answer can be checked objectively |

The old suites are kept in `archive/` so you can still re-run them or read
what earlier results were scored against.

The v1.2 prompts are:

1. Constrained writing: a lipogram acrostic poem
2. Code generation: strict Roman-numeral parsing
3. Reasoning: a logic grid with one solution
4. Long-input data extraction: log analysis
5. Multi-step math: tank fill rates over time
6. Language semantics: predicting exact output
7. Debugging: subtle Python bugs
8. Planning: critical path, answered as strict JSON

**Scores from different suite versions can't be compared.** The version is read
from the suite file's first line and stored with each run. `compare` warns you
when the runs you give it use different versions.

### Suite file format

`evalcore.parse_suite` expects each prompt to look like this:

```markdown
### 3. Prompt Name
**Prompt:**
> prompt text (blockquote markers are stripped; code blocks are kept)

**Target capabilities:** ...

**Scoring guide:**
...

---
```

## Usage

Run every command from the repo directory:

```bash
cd ~/.hermes/eval
```

### Automated run with a judge profile

```bash
python run_suite.py init                                         # create or upgrade history.db
python run_suite.py run --profile homepc --judge-profile nvidia  # judge defaults to nvidia
python run_suite.py run --profile local --prompts 1,3,7          # run only some prompts
python run_suite.py run --profile homepc --suite archive/suite_v1.1.md  # use an older suite
python run_suite.py run --profile nvidia --manual-score          # you score each reply
```

Each prompt is sent with
`hermes -p <profile> chat --query-file - -Q`, together with a short preamble
that tells the model to answer inline and not use tools. Each call runs in an
empty temporary directory, so an agentic profile can't touch the eval files.
The default timeout is 600 seconds per call (`--timeout`).

If the judge's reply can't be parsed, it is retried once. If it still fails, an
interactive run asks you for a score, and a non-interactive run leaves that
prompt unscored. Using the same profile as the model and the judge works, but
prints a warning about bias.

### Viewing history

```bash
python run_suite.py history                    # last 20 runs
python run_suite.py history --profile homepc --limit 50
python run_suite.py compare 28 29 30           # per-prompt scores side by side
```

In `compare`, `n/a` means the prompt wasn't part of that run, and `skip` means
it ran but has no score.

### Manual run

Use this when you run the prompts on the model yourself, for example in a chat
UI:

```bash
python eval_runner.py --profile claudepro [--model <name>] [--prompts 1,2]
```

For each prompt it prints the text, then reads the reply you paste. End the
paste with `END` on its own line or with Ctrl-D, type `@path/to/file` to load
the reply from a file, or type `SKIP`. Then you enter a score and optional
notes.

### Outside judge (for example Claude)

1. Collect the replies without scoring them:

   ```bash
   python collect_responses.py --profile nvidia --judge-label claude --judge-model claude-opus-5-5
   ```

   This creates a run with every score empty and writes
   `results/pending_<profile>_run<id>.json`.

2. Optionally run the mechanical checks for v1.2: line and word counts for the
   poem, a test harness for the Roman-numeral code, and JSON and answer-key
   checks for the critical path. They report facts, not scores.

   ```bash
   python auto_checks.py results/pending_nvidia_run19.json
   ```

3. Have the judge write a scores file:

   ```json
   {"run_id": 19, "judge": "Claude (claude-opus-5-5)",
    "scores": {"1": {"score": 7, "reasoning": "..."}, "2": {"score": 9, "reasoning": "..."}}}
   ```

4. Load the scores. This completes the run and writes the results report:

   ```bash
   python apply_scores.py scores_run19.json
   ```

### Maintenance

```bash
python verify_suite_v1_2.py          # recompute the v1.2 answer keys from the prompt text
python cleanup_history.py            # preview which runs would be removed
python cleanup_history.py --apply    # remove them (makes a timestamped backup first)
```

Run `verify_suite_v1_2.py` after editing any v1.2 prompt. The tank prompt (#5)
has its numbers hard-coded in the script, so update both together.

`cleanup_history.py` removes runs that aren't usable for v1.2 comparisons:
runs from other suite versions, partial runs, and runs that never completed.
Pending outside-judge runs are kept unless you add `--drop-pending`.

## Output

- **`history.db`** is the SQLite store, with tables `runs`, `results` and
  `prompts`. It is local only and gitignored, as are its backups
  (`history.backup_*.db`, `backup_*/`). Set `HERMES_EVAL_DB` to use a different
  database, for example a scratch one for testing.
- **`results/results_<profile>_run<id>_<YYYYMMDD>.md`** is the report for one
  run. It has a score table, every reply with the judge's reasoning, and an
  empty *Observations* section for your notes. Use `--output` to write it
  somewhere else.
- **`results/pending_<profile>_run<id>.json`** holds the raw replies from
  `collect_responses.py` while they wait for an outside judge.
- **`results/`** is local only and gitignored, like `history.db`

Treat existing files in `results/` as a record and don't edit them.

## Files

| File | Purpose |
|------|---------|
| `run_suite.py` | Main CLI: `init`, `run`, `history`, `compare` |
| `eval_runner.py` | Manual runner: you paste the replies and score them |
| `evalcore.py` | Shared code: suite parsing, database, profile lookup, reports |
| `collect_responses.py` | Collects replies without scoring them, for an outside judge |
| `auto_checks.py` | Mechanical checks for v1.2 prompts 1, 2 and 8 |
| `apply_scores.py` | Loads an outside judge's scores into a pending run |
| `verify_suite_v1_2.py` | Recomputes the v1.2 answer keys |
| `cleanup_history.py` | Removes old, partial and abandoned runs from `history.db` |
| `suite_v1.2.md` | Current prompt suite |
| `archive/` | Older suites (v1, v1.1) |
| `results/` | Run reports and pending replies |
