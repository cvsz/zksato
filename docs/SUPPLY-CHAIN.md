# Software supply-chain policy

## Source
Changes arrive through reviewable Git history. Generated or staged source must be reachable from the reviewed commit; do not rely on dangling blobs or post-review self-modifying workflows.

## CI/CD
- least-privilege `GITHUB_TOKEN` permissions;
- third-party Actions pinned to full immutable SHAs;
- workflow lint/security analysis;
- no production secrets in PR workflows;
- final validation bound to the head that is merged.

## Dependencies and artifacts
Use dependency audit/SAST/secret scanning, container vulnerability checks, SBOM generation, checksums, package metadata validation, and release re-verification. Attestation/signing features are capability/plan dependent and must not be claimed active unless enabled and verified.

## Containers
Use minimal non-root images, hardened runtime options where deployable, immutable image digests for deployment, and scan the final image rather than only manifests.

## Release provenance
Record source commit/tag, package/container digest, checksums/SBOM, workflow run, and verification result. Production authorization is a separate control.
