# Model Evaluation Suite v1.1
**Smoke test: 8 prompts × 1–10 scale = 80 max points**

> **Changes from v1** (scores from v1 and v1.1 are not directly comparable):
> - #2: asks for the code inline in the reply (agentic models were writing files instead).
> - #3: added a clue so the puzzle has exactly one solution (v1 had two).
> - #4: scoring guide lists which facts count, so the "most important" choice is less subjective.
> - #7: new buggy code with exactly 3 unambiguous bugs; removed draft notes from the scoring guide.
> - #8: format made unambiguous (exact lines, no list markers); scoring guide now enforces it.

---

## Scoring Rubric (1–10 per prompt)

| Score | Label | Criteria |
|-------|-------|----------|
| 10 | **Exemplary** | Perfect execution, nuanced, handles edge cases, shows insight |
| 9 | **Excellent** | Fully correct, well-structured, minor polish only |
| 8 | **Strong** | Correct, complete, minor omissions or awkward phrasing |
| 7 | **Good** | Mostly correct, one notable gap or error |
| 6 | **Adequate** | Core answer right, significant gaps or confusion |
| 5 | **Mediocre** | Half-right, half-wrong; major gaps |
| 4 | **Weak** | Missing key concepts, confused reasoning |
| 3 | **Poor** | Mostly wrong, hallucinates, fails instruction |
| 2 | **Very Poor** | Barely addresses prompt, incoherent |
| 1 | **Failure** | Refuses, nonsense, or completely off-topic |

**Scoring notes:**
- Deduct 1–2 for: not following format constraints, missing explicit requirements
- Deduct 1 for: verbosity when concise asked, or vice versa
- No half-points. Round down.

---

## Test Prompts

### 1. Instruction Following (Format Constraint)
**Prompt:**
> Write exactly three sentences about the water cycle. Each sentence must start with a different letter: first 'E', second 'C', third 'P'. No extra sentences, no extra words outside the three sentences.

**Target capabilities:** Hard constraint adherence, counting, format control

**Scoring guide:**
- 10: Exactly 3 sentences, correct starting letters, factually accurate water cycle
- 8–9: 3 sentences, correct letters, minor factual fuzziness
- 5–7: Wrong sentence count, wrong starting letters, or factually wrong
- 1–4: Doesn't attempt constraints

---

### 2. Code Generation (Python)
**Prompt:**
> Write a Python function `parse_duration(s: str) -> int` that parses duration strings like "2h30m", "45s", "1h", "3m15s" into total seconds. Handle invalid input with ValueError. Include type hints and a docstring. No external libraries. Give the complete function in a single Python code block in your reply; do not write it to a file.

**Target capabilities:** Clean code, edge cases, error handling, Python idioms

**Scoring guide:**
- 10: Handles all formats, validates input, clean readable code, good docstring
- 8–9: Works, minor style issues or missing one edge case (e.g., "0s")
- 5–7: Works for happy path only, crashes on valid variants
- 1–4: Syntax errors, wrong logic, uses regex poorly
- Deduct 2 if the code is not shown in the reply (e.g. only written to a file)

---

### 3. Reasoning (Logic Puzzle)
**Prompt:**
> Three people — Alice, Bob, Carol — each have a different favorite color: red, blue, green. Alice doesn't like red. Bob doesn't like blue. Bob doesn't like green. Carol's favorite is not green. Who likes what? Show your reasoning step by step, then give the final answer in this format: `Alice: X, Bob: Y, Carol: Z`.

**Target capabilities:** Logical deduction, step-by-step reasoning, format compliance

**Scoring guide:**
- Unique correct answer: `Alice: green, Bob: red, Carol: blue` (Bob can only be red → Carol can't be green so she's blue → Alice is green)
- 10: Correct deduction, clear steps, exact format
- 8–9: Correct answer, steps slightly messy, or format slightly off
- 5–7: Wrong answer but shows some logic, or right answer no steps
- 1–4: Guesses, no reasoning, wrong format

---

### 4. Summarization (Density + Accuracy)
**Prompt:**
> Summarize the following text in exactly 2 sentences, capturing only the three most important facts. No introductory phrases ("This text says...").

> *Text:* "The James Webb Space Telescope (JWST) launched December 25, 2021, on an Ariane 5 rocket from French Guiana. After a month-long journey, it reached its orbit at Sun-Earth L2, 1.5 million km from Earth. Its 6.5-meter primary mirror, composed of 18 hexagonal beryllium segments coated in gold, unfurled over two weeks. First science images released July 12, 2022, included the deepest infrared view of the universe (SMACS 0723), the Carina Nebula, Stephan's Quintet, and WASP-96b's atmospheric spectrum showing water vapor. JWST operates at ~40 K (-233 °C) via a five-layer sunshield the size of a tennis court. Mission design lifetime: 10+ years."

**Target capabilities:** Information extraction, compression, fact selection, constraint adherence

**Scoring guide:**
- Key facts (any 3 count; the best answers pick launch, L2 orbit, and first images or the mirror): launch Dec 25 2021 on Ariane 5; orbit at Sun-Earth L2 (1.5 million km); 6.5 m gold-coated beryllium mirror (18 segments); first images July 12 2022; ~40 K via tennis-court-sized sunshield; 10+ year design life
- Count a fact only if it's stated accurately. More than 3 facts = "wrong fact count".
- 10: Exactly 2 sentences, exactly 3 distinct key facts, no fluff, accurate
- 8–9: 2 sentences, 3 facts, minor extra words or slightly fuzzy fact
- 5–7: Wrong sentence count, wrong fact count, misses key facts
- 1–4: Copies text, hallucinates, ignores constraints

---

### 5. Creative Writing (Tone Control)
**Prompt:**
> Write a 50-word paragraph describing a thunderstorm from the perspective of a house cat. Tone: annoyed but not scared. No onomatopoeia words (boom, crash, zap, etc.). Count words exactly.

**Target capabilities:** Voice, constraint satisfaction (word count, banned words), creativity within bounds

**Scoring guide:**
- 10: Exactly 50 words, cat voice clear, annoyed not scared, no banned words
- 8–9: 48–52 words, good voice, maybe one banned word slip
- 5–7: Wrong word count, wrong tone, uses banned words
- 1–4: Not a paragraph, way off count, human perspective

---

### 6. Analysis (Trade-off Evaluation)
**Prompt:**
> Compare SQLite vs. PostgreSQL for a local-first desktop app that syncs occasionally to a central server. List 3 pros and 3 cons for each in a markdown table. No prose outside the table.

**Target capabilities:** Technical knowledge, structured output, balanced analysis, format discipline

**Scoring guide:**
- 10: Clean table, 3 pros/3 cons each, accurate technical points, no extra text
- 8–9: Table correct, maybe 2 pros/3 cons, or minor inaccuracy
- 5–7: Missing rows, wrong comparisons, prose outside table
- 1–4: Not a table, hallucinated features, biased

---

### 7. Debugging (Code Review)
**Prompt:**
> This Python code has exactly 3 bugs. Identify each bug, explain why it's wrong, and give the fix. Then show the corrected function.

```python
def moving_average(data: list[float], window: int) -> list[float]:
    """Return the mean of every full window of `window` consecutive items in `data`.

    Raises ValueError if window is not a positive integer.
    Returns [] if data has fewer than `window` items.
    """
    if window < 0:
        raise ValueError("window must be positive")
    result = []
    for i in range(len(data) - window):
        window_slice = data[i:i+window]
        result.append(sum(window_slice) / len(data))
    return result
```

**Target capabilities:** Code reading, bug finding, clear explanation, correct fix

**Scoring guide:**
- The 3 bugs:
  1. `if window < 0` lets `window == 0` through, but the docstring says it must be positive (and it leads to empty slices / a meaningless result). Fix: `if window <= 0`.
  2. `range(len(data) - window)` is off by one and drops the last window (e.g. `moving_average([1, 2, 3], 3)` returns `[]` instead of `[2.0]`). Fix: `range(len(data) - window + 1)`.
  3. Divides by `len(data)` instead of `window`, so every average is wrong. Fix: `/ window`.
- Not bugs: the `len(data) < window` case already returns `[]` (the range is empty), and `/` is float division in Python 3. Claiming either as one of the 3 bugs counts as a wrong "bug".
- 10: Finds all 3, explains each clearly, gives correct fixed code
- 8–9: Finds all 3, minor explanation gaps or small slip in the corrected code
- 5–7: Finds 2, or finds 3 but also reports a wrong "bug"
- 1–4: Finds 0–1, or mostly wrong "bugs"

---

### 8. Multi-step Planning (Task Decomposition)
**Prompt:**
> You need to migrate a 500 GB PostgreSQL database from on-prem to AWS RDS with < 4 hours downtime. List the 5 major steps in order, with one key risk per step. Output exactly 5 lines and nothing else. Each line must be formatted exactly `Step N: [action] — Risk: [risk]`, with no list markers or bullets before `Step`.

**Target capabilities:** Systems knowledge, practical ops experience, risk awareness, format compliance

**Scoring guide:**
- Format check: exactly 5 lines, each starting with `Step N:` (N = 1–5) and containing `— Risk:`. Extra text, list markers (`1.`, `-`), or bold count as format deviations (deduct 1–2).
- 10: 5 logical steps in correct order, realistic risks, exact format
- 8–9: 5 steps, order mostly right, risks plausible, format good
- 5–7: 3–4 steps, missing key steps (replication, cutover, validation), generic risks
- 1–4: Wrong steps, no risks, wrong format

---

## Running the Suite

```bash
cd ~/.hermes/eval

# Automated: each prompt goes to the profile via `hermes -p <profile> chat`,
# then a judge profile scores it (default judge: nvidia)
python run_suite.py run --profile homepc --judge-profile nvidia --suite suite_v1.1.md

# Automated answers, manual scoring
python run_suite.py run --profile nvidia --manual-score --suite suite_v1.1.md

# Fully manual: you run each prompt yourself and paste the reply (END to finish)
python eval_runner.py --profile nvidia --suite suite_v1.1.md

# History and comparisons
python run_suite.py history
python run_suite.py compare 4 5
```

Results markdown goes to `~/.hermes/eval/results/`. Every run is stored in `history.db` with the profile's model and the suite version.

---

## Results Template

```markdown
# Eval Results: <model> / <profile> / <date>

| # | Prompt | Score | Notes |
|---|--------|-------|-------|
| 1 | Instruction Following | /10 | |
| 2 | Code Generation | /10 | |
| 3 | Reasoning | /10 | |
| 4 | Summarization | /10 | |
| 5 | Creative Writing | /10 | |
| 6 | Analysis | /10 | |
| 7 | Debugging | /10 | |
| 8 | Planning | /10 | |
| **Total** | | **/80** | |

**Observations:**
- Strengths:
- Weaknesses:
- Notable failures:
- Compared to previous run:
```