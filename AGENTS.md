# Repository Instructions

These instructions apply to the entire repository.

## Required delivery workflow

All feature work must be delivered through a GitHub issue and a pull request.

1. Before implementation, create or identify one issue describing the goal, scope, and acceptance criteria.
2. Create a dedicated branch from the latest `main`. Never commit or push feature work directly to `main`.
3. Make the smallest independently useful and reviewable change that satisfies the issue.
4. Open a focused pull request linked to the issue and include the verification performed.
5. After required checks pass, agents may merge the pull request unless the maintainer asks them to wait for review.

If the requested work is too large for one small pull request, split it into multiple issues and deliver them sequentially. Each pull request must remain independently understandable and safe to merge.

## Minimum-change rule

- A pull request should address one concern only.
- Do not include opportunistic refactors, formatting sweeps, dependency upgrades, renames, or unrelated cleanup.
- Touch only the files and lines required for the issue.
- Prefer extending an existing abstraction over introducing a broad framework for possible future needs.
- Do not implement post-MVP behavior unless the issue explicitly requests it.
- Keep public interfaces and data formats unchanged unless changing them is part of the acceptance criteria.
- Add only tests and documentation directly needed to verify or explain the change.

When two requested changes can be reviewed, tested, or reverted independently, treat them as separate issues and pull requests.

## Issue requirements

Every implementation issue should state:

- The user-visible or technical outcome.
- What is in scope.
- What is explicitly out of scope.
- Concrete acceptance criteria.
- Relevant dependencies or blocking issues.

Clarify ambiguous requirements in the issue before writing code when different interpretations would materially change the implementation.

## Pull request requirements

Every pull request should:

- Link its issue with `Closes #<number>` when appropriate.
- Explain the outcome, not just list edited files.
- State the tests or checks that were run.
- Call out known limitations without expanding the PR to fix unrelated ones.
- Avoid combining generated artifacts, source changes, and broad documentation revisions unless all are required by the same issue.

Agents must report the pull request URL and validation status. They may merge a passing pull request, but must not bypass required checks or directly push its changes to `main`.

## Repository direction

Use `SPEC.md` as the product and technical source of truth. Keep MVP work aligned with its milestones and non-goals. If a requested implementation conflicts with the spec, describe the conflict in the issue or pull request rather than silently broadening the design.
