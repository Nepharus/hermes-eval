# Model Evaluation Suite v1.2
**Harder suite: 8 prompts × 1–10 scale = 80 max points**

> **Why v1.2:** on v1.1, gemma4:12b scored 79/80, so v1.1 can no longer tell good models apart. Every v1.2 prompt has an objectively checkable answer
> (exact numbers, a unique puzzle solution, test cases, exact output), and several contain deliberate traps. The answer keys were verified by
> `verify_suite_v1_2.py`. Scores are not comparable with v1 or v1.1.

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
- A wrong final answer caps the score at 5, however good the explanation is.
- Deduct 1–2 for: not following format constraints, missing explicit requirements
- Deduct 1 for: verbosity when concise asked, or vice versa
- No half-points. Round down.

---

## Test Prompts

### 1. Constrained Writing (Multiple Hard Constraints)
**Prompt:**
> Write a four-line poem about a lighthouse. Rules: (1) the first letters of the four lines spell S, A, L, T in that order; (2) every line has exactly 7 words (a hyphenated word counts as one word); (3) the last words of line 2 and line 4 rhyme; (4) the letter "e" (upper or lower case) must not appear anywhere in the poem; (5) output only the four lines, with no title or commentary.

**Target capabilities:** Satisfying several simultaneous hard constraints, self-checking, letter-level control

**Scoring guide:**
- Check each rule separately. Count words per line and search every word for the letter "e"; do not trust the model's own claims.
- 10: All 5 rules met, and the poem is about a lighthouse
- 8–9: All rules met except one line off by one word
- 6–7: Exactly one rule clearly broken (e.g. one "e" appears, or the rhyme fails)
- 4–5: Two rules broken
- 1–3: Three or more rules broken, or not a poem about a lighthouse

---

### 2. Code Generation (Strict Validation)
**Prompt:**
> Write a Python function `roman_to_int(s: str) -> int` that converts a Roman numeral to an integer, accepting ONLY canonical uppercase Roman numerals from 1 to 3999 (standard subtractive notation: IV, IX, XL, XC, CD, CM). Any non-canonical or invalid input must raise ValueError. Do not use external libraries. Give the complete function in a single Python code block in your reply; do not write it to a file.

**Target capabilities:** Precise specification handling, input validation, edge cases

**Scoring guide:**
- Must return: "I"→1, "IV"→4, "IX"→9, "XIV"→14, "XL"→40, "XCIX"→99, "CDXLIV"→444, "MCMXCIV"→1994, "MMMCMXCIX"→3999
- Must raise ValueError for: "" (empty), "IIII", "VV", "IIV", "IC", "IL", "XM", "VX", "XCX", "CMC", "MMMM", "iv" (lowercase), "XIV " (trailing space), "ABC"
- Trace the code against these cases; don't assume. Typical failures: accepting "IIII", "IC", "XCX" or "MMMM".
- 10: All valid cases correct and all invalid cases rejected, clean code, docstring/type hints
- 8–9: Correct except 1 invalid case accepted
- 5–7: Valid cases correct but 2–4 invalid cases accepted
- 1–4: Wrong values for valid input, or accepts most invalid input

---

### 3. Reasoning (Logic Grid)
**Prompt:**
> Ana, Ben, Cy and Dee sit in seats 1–4, numbered left to right. Each has a different pet (cat, dog, fish, bird) and a different drink (tea, coffee, juice, milk).
> 1. The dog owner sits immediately to the right of the tea drinker.
> 2. Ana does not sit at either end.
> 3. There is exactly one seat between Ben and the fish owner.
> 4. Cy drinks milk.
> 5. The coffee drinker sits in seat 4.
> 6. Dee owns neither the cat nor the dog.
> 7. The bird owner sits somewhere to the left of the cat owner.
> 8. Ana does not drink juice.
> 9. Cy and Dee do not sit next to each other.
>
> Find each person's seat, pet and drink. Show your reasoning, then give the final answer as four lines in exactly this format: `Name: seat N, pet, drink`, ordered by seat.

**Target capabilities:** Multi-constraint deduction, eliminating cases, format compliance

**Scoring guide:**
- Unique solution (verified by brute force):
  `Dee: seat 1, bird, juice` / `Ana: seat 2, fish, tea` / `Cy: seat 3, dog, milk` / `Ben: seat 4, cat, coffee`
- Without clue 9 there are 3 solutions, so an answer that never uses clue 9 is guessing.
- 10: Correct, reasoning sound and complete, exact format
- 8–9: Correct, reasoning has a gap or format slightly off
- 4–5: One or two attributes wrong
- 1–3: Mostly wrong, or the answer violates a clue

---

### 4. Long-Input Data Extraction (Log Analysis)
**Prompt:**
> Below is an authentication log. Consider only LOGIN_FAIL events with a timestamp from 02:00:00 to 03:59:59 inclusive whose IP address is outside the 10.0.0.0/8 network. (1) Which user has the most such events, and how many? (2) What is the total number of such events across all users? Give the two answers on the first two lines as `top: <user> <count>` and `total: <count>`, then briefly explain your method.
>
> ```
> 01:41:30 LOGIN_FAIL user=fkim    ip=100.64.3.2
> 01:44:37 LOGIN_FAIL user=dpatel  ip=172.16.5.5
> 01:46:28 LOGIN_OK   user=eve     ip=10.0.4.12
> 01:48:54 LOGIN_FAIL user=eve     ip=10.0.9.33
> 01:51:21 LOGIN_FAIL user=eve     ip=203.0.113.9
> 01:55:07 LOGOUT     user=fkim    ip=203.0.113.9
> 01:58:58 LOGOUT     user=fkim    ip=10.2.0.7
> 02:01:59 LOGIN_FAIL user=gwu     ip=100.64.3.2
> 02:03:44 LOGIN_FAIL user=alice   ip=10.0.4.12
> 02:07:44 LOGIN_FAIL user=dpatel  ip=10.0.9.33
> 02:08:13 LOGIN_FAIL user=dpatel  ip=10.0.9.33
> 02:11:04 LOGIN_OK   user=eve     ip=100.64.3.2
> 02:11:38 LOGIN_FAIL user=dpatel  ip=198.51.100.23
> 02:12:35 LOGIN_OK   user=fkim    ip=203.0.113.9
> 02:13:28 LOGOUT     user=eve     ip=203.0.113.9
> 02:14:51 LOGIN_FAIL user=alice   ip=203.0.113.9
> 02:17:40 LOGIN_OK   user=gwu     ip=10.0.9.33
> 02:18:35 LOGIN_OK   user=bmoss   ip=192.0.2.44
> 02:19:21 LOGIN_FAIL user=fkim    ip=10.0.9.33
> 02:21:38 LOGIN_FAIL user=chen    ip=203.0.113.9
> 02:22:17 LOGOUT     user=chen    ip=10.0.4.12
> 02:23:54 LOGOUT     user=bmoss   ip=192.0.2.44
> 02:26:53 LOGIN_FAIL user=alice   ip=198.51.100.23
> 02:28:08 LOGIN_FAIL user=fkim    ip=192.0.2.44
> 02:30:39 LOGIN_OK   user=fkim    ip=198.51.100.23
> 02:34:21 LOGIN_OK   user=chen    ip=10.0.4.12
> 02:36:33 LOGIN_FAIL user=chen    ip=100.64.3.2
> 02:38:49 LOGIN_OK   user=bmoss   ip=198.51.100.23
> 02:41:14 LOGIN_FAIL user=fkim    ip=100.64.3.2
> 02:42:28 LOGIN_OK   user=dpatel  ip=10.0.4.12
> 02:43:40 LOGIN_OK   user=fkim    ip=10.2.0.7
> 02:47:26 LOGIN_FAIL user=eve     ip=100.64.3.2
> 02:50:11 LOGOUT     user=chen    ip=172.16.5.5
> 02:50:39 LOGIN_OK   user=gwu     ip=172.16.5.5
> 02:53:26 LOGIN_FAIL user=chen    ip=172.16.5.5
> 02:56:57 LOGIN_OK   user=eve     ip=172.16.5.5
> 02:59:13 LOGOUT     user=eve     ip=203.0.113.9
> 03:01:55 LOGIN_FAIL user=fkim    ip=10.0.4.12
> 03:04:58 LOGIN_OK   user=chen    ip=172.16.5.5
> 03:06:22 LOGIN_FAIL user=chen    ip=203.0.113.9
> 03:10:04 LOGOUT     user=eve     ip=203.0.113.9
> 03:12:37 LOGIN_OK   user=eve     ip=10.0.9.33
> 03:13:27 LOGIN_OK   user=alice   ip=192.0.2.44
> 03:14:39 LOGIN_FAIL user=dpatel  ip=100.64.3.2
> 03:18:20 LOGIN_FAIL user=chen    ip=10.0.4.12
> 03:19:01 LOGIN_OK   user=dpatel  ip=100.64.3.2
> 03:22:31 LOGOUT     user=chen    ip=172.16.5.5
> 03:26:26 LOGIN_OK   user=alice   ip=100.64.3.2
> 03:28:57 LOGOUT     user=chen    ip=10.0.9.33
> 03:30:13 LOGIN_OK   user=eve     ip=10.0.4.12
> 03:32:18 LOGIN_FAIL user=bmoss   ip=198.51.100.23
> 03:33:54 LOGIN_FAIL user=chen    ip=203.0.113.9
> 03:36:10 LOGIN_OK   user=eve     ip=192.0.2.44
> 03:39:16 LOGIN_FAIL user=bmoss   ip=203.0.113.9
> 03:40:06 LOGIN_OK   user=alice   ip=172.16.5.5
> 03:40:58 LOGIN_FAIL user=bmoss   ip=10.0.9.33
> 03:44:24 LOGIN_OK   user=fkim    ip=10.2.0.7
> 03:46:03 LOGOUT     user=fkim    ip=10.2.0.7
> 03:48:06 LOGIN_FAIL user=gwu     ip=192.0.2.44
> 03:48:43 LOGIN_FAIL user=gwu     ip=192.0.2.44
> 03:51:16 LOGIN_FAIL user=alice   ip=192.0.2.44
> 03:53:34 LOGIN_OK   user=bmoss   ip=198.51.100.23
> 03:57:31 LOGOUT     user=alice   ip=172.16.5.5
> 03:59:37 LOGIN_FAIL user=alice   ip=198.51.100.23
> 04:02:35 LOGIN_OK   user=bmoss   ip=100.64.3.2
> 04:03:52 LOGOUT     user=eve     ip=172.16.5.5
> 04:04:41 LOGIN_OK   user=bmoss   ip=192.0.2.44
> 04:07:45 LOGIN_OK   user=gwu     ip=198.51.100.23
> 04:10:25 LOGIN_FAIL user=gwu     ip=172.16.5.5
> 04:13:52 LOGIN_OK   user=fkim    ip=10.0.4.12
> 04:16:12 LOGIN_OK   user=eve     ip=172.16.5.5
> 04:17:17 LOGIN_FAIL user=chen    ip=172.16.5.5
> 04:19:31 LOGIN_OK   user=alice   ip=203.0.113.9
> 04:20:41 LOGIN_FAIL user=gwu     ip=100.64.3.2
> ```

**Target capabilities:** Careful filtering over long input, IP-range reasoning, counting accuracy

**Scoring guide:**
- Correct answer: `top: chen 5` and `total: 19`
- Traps: 172.16.x.x and 100.64.x.x are private/shared ranges but are OUTSIDE 10.0.0.0/8, so they count. Events at 01:5x and 04:0x are outside the window. Counting internal IPs too gives chen 6; counting every LOGIN_FAIL in the whole log gives chen 7.
- 10: Both answers correct, exact format
- 8–9: Both correct, format slightly off
- 5–6: Exactly one of the two answers correct
- 1–4: Both wrong

---

### 5. Multi-step Math (Rates Over Time)
**Prompt:**
> A 1,200-litre tank starts 25% full. Pipe A fills a full tank in 6 hours and pipe B fills a full tank in 4 hours. Drain C empties a full tank in 8 hours. At 09:00 pipes A and B are opened. At 10:00 drain C is opened. At 10:30 pipe B is closed. A and C stay open. At what clock time does the tank become full? Show your working, then give the final answer on its own line as `Full at HH:MM`.

**Target capabilities:** Multi-phase rate problems, unit handling, careful arithmetic

**Scoring guide:**
- Rates: A +200 L/h, B +300 L/h, C −150 L/h. Start 300 L.
- 09:00–10:00: +500 → 800 L. 10:00–10:30: net +350 L/h × 0.5 h → 975 L. After 10:30: net +50 L/h, so 225 L takes 4.5 h.
- Correct answer: `Full at 15:00`
- Trap: assuming B stays open gives about 11:09.
- 10: Correct, clear working, exact format
- 8–9: Correct, working messy or format off
- 4–5: Correct method, one arithmetic slip
- 1–3: Wrong method or answer

---

### 6. Language Semantics (Exact Output Prediction)
**Prompt:**
> What exactly does this Python 3 line print? Give the exact output line first, then a one-sentence reason for each of the 8 values.
>
> ```python
> print(round(2.5), round(3.5), round(-0.5), int(-3.7), -7 // 2, -7 % 3, 0.1 + 0.2 == 0.3, [1, 2, 3][-4:2])
> ```

**Target capabilities:** Precise language knowledge (banker's rounding, floor division, modulo sign, float error, slicing)

**Scoring guide:**
- Exact output: `2 4 0 -3 -4 2 False [1, 2]`
- Reasons: round() uses round-half-to-even (2.5→2, 3.5→4, −0.5→0, printed as `0` because it's an int); int() truncates toward zero; // floors toward −∞; % takes the sign of the divisor; 0.1+0.2 is 0.30000000000000004; out-of-range slice starts are clamped.
- 10: Exact output and all reasons correct
- 8–9: Exact output, one reason weak or wrong
- 6–7: One value wrong
- 4–5: Two values wrong
- 1–3: Three or more values wrong

---

### 7. Debugging (Subtle Python Bugs)
**Prompt:**
> `total_scaled([1, 2, 3], [2, 3])` should return `[28, 42, 14]`, and the caller's list must be unchanged afterwards. The code below has exactly 3 bugs. Identify each one, explain the mechanism, give the fix, then show the corrected code. Also state what the buggy version actually returns for that call.
>
> ```python
> def make_multipliers(factors=[]):
>     """Return one multiplier function per factor, plus an identity (x1) multiplier.
>     Must not modify the caller's list."""
>     factors.append(1)
>     return [lambda x: x * f for f in factors]
>
> def total_scaled(values, factors):
>     """For each multiplier, return the sum of multiplier(v*v) over values."""
>     mults = make_multipliers(factors)
>     squared = (v * v for v in values)
>     return [sum(m(s) for s in squared) for m in mults]
> ```

**Target capabilities:** Understanding closures, mutability and iterator semantics; explaining root causes

**Scoring guide:**
- The 3 bugs:
  1. `factors.append(1)` changes the list in place: it modifies the caller's list (it becomes [2, 3, 1]) and, through the mutable default `[]`, accumulates across calls. Fix: `factors = list(factors or []) + [1]` with `factors=None` as the default.
  2. Late binding: every lambda looks up `f` when it is called, so they all use the last factor (1). Fix: `lambda x, f=f: x * f`.
  3. `squared` is a generator, so it's used up by the first multiplier and the rest sum over nothing. Fix: use a list.
- Buggy return value: `[14, 0, 0]`. Fixed: `[28, 42, 14]`.
- 10: All 3 bugs with correct mechanisms, correct fixed code, correct buggy output
- 8–9: All 3 bugs; buggy output missing or wrong
- 5–7: 2 bugs found
- 1–4: 0–1 bugs, or wrong explanations

---

### 8. Planning (Critical Path, Strict JSON)
**Prompt:**
> A project has these tasks (duration in days; a task can start only when all its prerequisites have finished; unlimited workers):
> A 3 (none); B 5 (A); C 2 (A); D 4 (C); E 6 (B); F 3 (B, D); G 7 (C); H 2 (E, F); I 4 (G, H).
> Output ONLY a JSON object, with no code fences or other text, of the form:
> {"project_days": <int>, "critical_path": [<task letters in order>], "slack": {"A": <int>, ..., "I": <int>}}
> where slack is how many days each task can be delayed without delaying the project.

**Target capabilities:** Dependency scheduling, forward/backward pass, strict machine-readable output

**Scoring guide:**
- Correct answer: `{"project_days": 20, "critical_path": ["A","B","E","H","I"], "slack": {"A":0,"B":0,"C":2,"D":2,"E":0,"F":2,"G":4,"H":0,"I":0}}`
- Traps: path A-C-G-I is only 16 days (G slack 4); paths through F (A-B-F-H-I = 17, A-C-D-F-H-I = 18) are not critical.
- 10: Valid JSON only, all values correct
- 8–9: All values correct but has code fences or extra text
- 5–7: project_days and critical_path correct, 1–3 slack values wrong
- 1–4: Wrong project_days or critical_path, or not JSON

---

## Running the Suite

```bash
cd ~/.hermes/eval
python run_suite.py run --profile homepc --judge-profile nvidia     # automated (v1.2 is the default)
python run_suite.py run --profile nvidia --suite archive/suite_v1.1.md      # older suite
python verify_suite_v1_2.py                                         # re-check the answer keys
```

---

## Results Template

```markdown
# Eval Results: <model> / <profile> / <date>

| # | Prompt | Score | Notes |
|---|--------|-------|-------|
| 1 | Constrained Writing | /10 | |
| 2 | Code Generation | /10 | |
| 3 | Logic Grid | /10 | |
| 4 | Log Analysis | /10 | |
| 5 | Multi-step Math | /10 | |
| 6 | Output Prediction | /10 | |
| 7 | Debugging | /10 | |
| 8 | Critical Path | /10 | |
| **Total** | | **/80** | |
```
