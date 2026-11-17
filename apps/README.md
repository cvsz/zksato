# Applications (placeholders)

Deployable entry points for the `packages/*` monorepo. **Not yet implemented:**
each directory holds only a `pyproject.toml` that declares `packages = ["src"]`,
but no `src/` exists yet.

| App | Intended role | Depends on |
|-----|---------------|------------|
| `api/` | API server (uvicorn/gunicorn) | `zksato-api` |
| `cli/` | operator CLI | `zksato-cli` |
| `worker/` | background worker | `zksato-automation`, `zksato-broker`, `zksato-portfolio` |

The running service today is the legacy package: `uvicorn zksato.api:app`
(`src/zksato/`, see `../Dockerfile`). See `../docs/PROJECT-STRUCTURE.md`.
