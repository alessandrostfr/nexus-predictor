# AI-Assisted Development Workflow

## Goal

This project uses AI agents as controlled assistants, not as autonomous developers.

The human developer remains responsible for planning, reviewing, validating, and committing changes.

## Standard workflow

1. Define the task.
2. Review the roadmap or current objective.
3. Ask the agent to inspect the repository without editing.
4. Request a plan.
5. Approve or reject the plan.
6. Let the agent implement a small scoped change.
7. Review the diff.
8. Run validations.
9. Perform manual UI checks if needed.
10. Commit with an English message.

## Branch strategy

Use feature branches for meaningful work.

Example:

git checkout -b feature/example-task

Use hotfix branches for small fixes.

Example:

git checkout -b hotfix/example-fix

## Commit rules

- Commit messages must be in English.
- Commits should be small and meaningful.
- Do not commit generated secrets, local files, virtual environments, logs, or .env files.

## Human review checklist

Before committing:

- git status is reviewed.
- git diff is reviewed.
- Tests/builds are executed when relevant.
- UI is manually checked when frontend changes are made.
- No unrelated files were modified.
