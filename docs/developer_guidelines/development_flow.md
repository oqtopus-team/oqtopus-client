# Development Flow

## Branch strategy

Recommended branch naming:

- `feature/<name>` for new features
- `bugfix/<name>` for bug fixes
- `hotfix/<name>` for urgent fixes

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) when possible.

Examples:

- `feat: add typed helper for estimation job`
- `fix: handle timeout error payload`
- `docs: update developer guidelines`
- `test: add constructor fallback coverage`

## Pull requests

- Keep PRs focused and small.
- Include tests for behavior changes.
- Update docs when public APIs or contributor workflows change.
- If generated code changes, include the source spec change and generation command in the PR description.
