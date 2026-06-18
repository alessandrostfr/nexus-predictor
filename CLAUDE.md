# Claude Code Instructions

Claude Code must follow `AGENTS.md` first.

## Operating mode

- Start in analysis/planning mode.
- Do not edit files immediately.
- Before making changes, explain the plan and list affected files.
- Prefer small patches over large rewrites.
- Ask for approval before modifying more than 2 files.
- Ask for approval before changing architecture, database schema, authentication, permissions, deployment, or security-related code.

## Repository behavior

- Read the existing structure before proposing changes.
- Reuse existing conventions.
- Do not introduce unnecessary dependencies.
- Do not rename files, move folders, or delete code unless explicitly requested.
- Do not generate placeholder production logic.
- Do not fake tests or validation results.

## Communication

- Repository files, comments, documentation, and commit messages must be written in English.
- Explanations to Alessandro can be in Spanish.
- Be explicit about uncertainty.
- Separate confirmed facts from assumptions.

## Validation

At the end of each task, provide:

- files changed;
- commands executed;
- commands still required if not executed;
- manual validation steps;
- risks;
- suggested commit message.

## Privacy

Never reveal or write secrets.
Never use real customer/company data in examples.
Never add `.env` files to Git.
