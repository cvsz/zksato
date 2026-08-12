# Disaster Recovery (DR) Drill Runbook

## Overview
This document outlines the procedures for conducting RPO/RTO disaster recovery drills. Regular drills ensure that our infrastructure can be restored within our Recovery Point Objective (RPO) and Recovery Time Objective (RTO) targets.

## Objectives
- **RTO (Recovery Time Objective):** 4 hours
- **RPO (Recovery Point Objective):** 1 hour

## Drill Execution Steps

### 1. Preparation
- Notify stakeholders of the upcoming DR drill.
- Ensure monitoring and logging are active.

### 2. Simulation (Failover)
- Simulate a regional failure or database corruption.
- Isolate the primary database/service.

### 3. Recovery (Failback)
- Provision a new database instance using Terraform.
- Restore the latest backup from AWS KMS encrypted S3 bucket.
- Update DNS/routing to point to the new infrastructure.
- Validate data integrity and service health.

### 4. Post-Drill Analysis
- Calculate actual RTO and RPO achieved.
- Identify bottlenecks and update this runbook accordingly.
