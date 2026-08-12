---
applyTo: ".github/workflows/**/*.yml"
---
Use least-privilege workflow permissions, immutable full-SHA pins for third-party Actions, explicit timeouts/concurrency, and no production secrets in pull-request context. Do not use GITHUB_TOKEN self-push orchestration to mutate source after review. Required checks must validate the exact head that is merged. Plan-gated features must fail safely or be capability-gated and documented.
