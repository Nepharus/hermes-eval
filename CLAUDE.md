# Hermes eval suite

## Git workflow
- Never commit to or push main. Create a branch for each change: feature/<short-name> or fix/<short-name>.
- Commit in small, clearly described steps.
- When done, push the branch and open a PR with `gh pr create`, including a summary of what changed and how it was tested.
- Never merge PRs. The repo owner reviews and merges.
- Never use --no-verify or force-push.

## Files
- history.db and backups are local only and gitignored. Don't modify history.db unless asked.
- results/ holds run outputs and is local only (gitignored). Don't edit existing result files.

## Running evals
- Run one eval at a time. Don't start run_suite.py, collect_responses.py or eval_runner.py while another run is in progress, including in the background or for a different profile.
- Within a run, send prompts one after another. Don't parallelize prompts or judge calls (e.g. with threads, `&` or xargs -P).
- Why: parallel runs compete for the same local GPU and API rate limits, which skews timings, causes timeouts and makes scores less comparable between runs.
