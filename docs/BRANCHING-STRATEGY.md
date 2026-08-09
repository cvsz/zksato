# Branching strategy

## Model
Use short-lived branches from `main`. `main` represents reviewed source, not proof of production deployment.

Recommended prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `ci/`, `ops/`, `security/`, `risk/`, `strategy/`, `hotfix/`.

## Rules
- one coherent concern per PR;
- rebase/update with current `main` before final validation when necessary;
- final checks must apply to the head that is merged;
- do not use self-mutating workflows to replace source after review;
- do not force-push shared/reviewed branches unless coordinated;
- prefer squash merge for a coherent feature/fix when repository policy allows it.

## Protected-main target
Where supported, require PR review, status checks, conversation resolution, no force push/deletion, and deployment/environment controls for production changes. Actual GitHub settings are external configuration and must be audited separately.
