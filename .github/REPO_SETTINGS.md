# Repository Settings

Recommended GitHub repository settings for Mergewall.

## Description

```
AI Merge Governance Runtime — block high-risk AI-generated code from entering production.
```

## Topics

```
merge-governance ai-safety code-review security github ci-cd python langgraph risk-management pr-review deterministic-guards
```

## Branch Protection (main)

- [ ] Require a pull request before merging
- [ ] Require status checks to pass before merging
  - [ ] `test (3.10)`
  - [ ] `test (3.11)`
  - [ ] `test (3.12)`
- [ ] Require conversation resolution before merging

## GitHub App

Mergewall requires a GitHub App with the following permissions:

- **Checks**: Read & write (to create check runs that block merges)
- **Pull Requests**: Read & write (to fetch diffs and post comments)
- **Contents**: Read (to access repository code)

Webhook events:
- `pull_request.opened`
- `pull_request.synchronize`
