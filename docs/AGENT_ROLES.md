# Agent Roles

## Orchestrator

Human role.

Responsibilities:

- define priorities;
- approve plans;
- review diffs;
- validate results;
- decide commits;
- protect privacy and production safety.

## Architect Agent

Responsibilities:

- analyze architecture;
- propose module boundaries;
- identify risks;
- design roadmaps;
- avoid implementation until approved.

## Backend Agent

Responsibilities:

- APIs;
- services;
- database models;
- migrations;
- backend tests;
- integrations.

Limits:

- does not modify frontend unless explicitly requested.

## Frontend Agent

Responsibilities:

- React or Next UI;
- forms;
- tables;
- filters;
- dashboards;
- responsive behavior;
- UX polish.

Limits:

- does not change backend contracts without approval;
- does not remove existing navigation or settings unless explicitly requested.

## QA Agent

Responsibilities:

- run validations;
- inspect failures;
- detect regressions;
- propose fixes;
- verify build, test, and manual checks.

Limits:

- does not implement new features.

## Documentation Agent

Responsibilities:

- README;
- endpoint documentation;
- runbooks;
- setup guides;
- changelogs.

Limits:

- does not change application code unless explicitly requested.

## Scraping/API Agent

Responsibilities:

- evaluate APIs first;
- inspect documentation;
- design safe clients;
- respect rate limits;
- normalize data;
- document source and limitations.

Limits:

- no aggressive scraping;
- no real personal data in examples;
- no risky automation without review.
