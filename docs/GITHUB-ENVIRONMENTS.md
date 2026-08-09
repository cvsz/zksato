# GitHub environments

## `uat`
Use for broker UAT certification workflows. Store only UAT-specific secrets, use required reviewers where supported, and restrict deployments to intended refs.

## `production`
Use for production-readiness/deployment workflows. Protect credentials, require explicit human approval, restrict branches/tags, and separate environment secrets from PR context.

## Principles
- no production secrets in pull-request workflows;
- environment approval does not bypass application risk/approval gates;
- UAT evidence does not imply production permission;
- workflow YAML referencing an environment does not prove the environment exists or is protected.

Record current setup in readiness evidence rather than hard-coding secret values.
