# Security and Privacy Rules

## Secrets

Never commit:

- .env files;
- API keys;
- private keys;
- database passwords;
- tokens;
- real credentials;
- production dumps.

## Personal and company data

Do not use real data in:

- prompts;
- tests;
- fixtures;
- documentation examples;
- screenshots;
- logs.

Use fake data instead.

## AI usage

Before using AI tools with project data:

- remove secrets;
- anonymize personal data;
- avoid production datasets;
- avoid exposing customer, owner, lead, property, employee, or internal CRM information.

## Production safety

Agents must not:

- deploy to production without explicit approval;
- run destructive database commands without explicit approval;
- delete files without explicit approval;
- modify authentication, permissions, billing, or security logic without review.
