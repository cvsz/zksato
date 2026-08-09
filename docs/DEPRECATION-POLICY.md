# Deprecation policy

Public API/config/schema behavior should not be removed silently.

## Process
1. document the deprecated behavior and replacement;
2. add warnings/compatibility period when safe;
3. identify affected operators/integrations;
4. update OpenAPI/docs/examples;
5. provide migration/rollback guidance;
6. remove only in an appropriate release with tests proving the intended break.

Security or execution-safety defects may require accelerated removal. In that case document the reason and operational migration path.

Database migrations are append-only once released; do not rewrite historical migration files to emulate deprecation.
