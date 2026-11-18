# Hermes eval suite

## Git workflow
- Never commit to or push main. Create a branch for each change: feature/<short-name> or fix/<short-name>.
- Commit in small, clearly described steps.
- When done, push the branch and open a PR with `gh pr create`, including a summary of what changed and how it was tested.
- Never merge PRs. The repo owner reviews and merges.
- Never use --no-verify or force-push.

## Files
- history.db and backups are local only and gitignored. Don't modify history.db unless asked.
- results/ holds run outputs. Don't edit existing result files.
- results/ holds run outputs and is local only (gitignored). Don't edit existing result files.
