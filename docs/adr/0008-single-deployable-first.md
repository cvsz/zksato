# ADR-0008: Modular single deployable before microservices

Status: Accepted

## Decision
Keep a modular Python/FastAPI application until measurable scale/failure-domain needs justify extraction. Use explicit interfaces so market ingestion, workers, and read APIs can be separated later.

## Consequences
Lower operational complexity while correctness matures; requires discipline around module boundaries.
