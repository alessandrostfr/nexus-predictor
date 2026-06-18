# Agent Working Rules

## Human role

The human developer is the orchestrator.

AI agents must support development, but the human developer decides the roadmap, approves plans, reviews changes, validates results, and creates commits.

## Core rules

- Do not modify files before explaining the plan.
- Do not change unrelated files.
- Keep changes small, focused, and reviewable.
- Never delete existing functionality unless explicitly requested.
- Never make broad architectural changes without approval.
- Always preserve existing UX, navigation, settings, language selectors, and working features unless the task explicitly asks to change them.
- Use English for code comments, commit messages, technical documentation, and repository files.
- Use Spanish only when explaining the work to the human developer.
- Always explain:
  - what changed;
  - which files changed;
  - how to validate;
  - risks or assumptions;
  - suggested English commit message.

## Privacy and data protection

- Never expose secrets, tokens, private keys, credentials, or real personal data.
- Never commit `.env` files.
- Do not use real company, customer, property, owner, lead, tenant, employee, or internal CRM data in examples.
- Use fake/demo data for tests, documentation, and examples.
- Ask for clarification before handling sensitive data, production data, billing, credentials, or irreversible actions.

## Workflow

For each task:

1. Understand the objective.
2. Inspect the relevant files.
3. Propose a plan before editing.
4. Wait for approval if the task touches multiple files, architecture, security, database schema, or frontend layout.
5. Implement the smallest safe change.
6. Run or propose validation commands.
7. Summarize the diff.
8. Suggest an English commit message.

## Validation expectations

Before considering a task complete, provide the relevant checks:

- Static checks.
- Backend tests if backend/scripts are touched.
- Frontend build if frontend is touched.
- Docker validation if services or compose files are touched.
- Git status check.
- Manual UI checklist if frontend is touched.
- No-regression checklist for existing features.
