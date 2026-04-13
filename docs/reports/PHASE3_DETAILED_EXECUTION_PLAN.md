# Phase 3 Detailed Execution Plan

Date: 2026-04-13
Status: Draft, pending user approval
Scope: Remaining platform hardening after Phase 2 completion

## Goal

Complete post-Phase-2 hardening with deterministic operations by:
- closing RBAC coverage gaps,
- aligning security and configuration behavior,
- making analytics fallback/cache behavior observable and deterministic,
- decoupling dbt runtime from Airflow into a standalone service without regression.

## Constraints and assumptions

- Phase 2 outputs are accepted as baseline and remain serving source of truth.
- Zero tolerance for cross-tenant leakage in API and ML serving paths.
- dbt migration to standalone service must preserve DAG contract and daily ETL reliability.
- Commit policy remains gate-based: no commit without explicit user approval.

## Big step 1: RBAC coverage audit and enforcement closure

### Task 1.1: Build endpoint-role matrix from live routers
- Enumerate all endpoints in backend modules:
  - auth, users, partners, finance, analytics, settings
- For each endpoint, record:
  - required auth dependency,
  - role gate (if any),
  - tenant filter strategy in service layer.

### Task 1.2: Detect and patch missing role checks
- Focus on mutating operations (`POST`, `PUT`, `PATCH`, `DELETE`, state transitions).
- Ensure high-risk transitions (posting invoices/bills, user management, settings updates) are role-guarded.
- Apply minimal code changes; keep APIs stable.

### Task 1.3: Add regression tests for role enforcement
- Add targeted backend tests:
  - allowed roles receive success,
  - forbidden roles receive 403,
  - unauthenticated requests receive 401.

Validation evidence to record:
- endpoint-role matrix report,
- list of patched endpoints,
- test run summary (pass/fail counts).

Gate A:
- User approves RBAC closure before moving to Big step 2.

## Big step 2: Security and configuration consistency hardening

### Task 2.1: Centralize runtime config references
- Verify all core services read config from a single source (env/config module), including:
  - JWT/security settings,
  - MLflow URI,
  - Trino/MinIO/Postgres endpoints,
  - cache settings.

### Task 2.2: Remove drift between compose/env/code defaults
- Compare `docker-compose.yml`, backend config, Airflow config, and ML scripts.
- Patch mismatched defaults that can cause silent environment skew.

### Task 2.3: Add defensive startup logging for critical config
- Log sanitized effective values (hostnames, toggles, versions, not secrets) at startup.
- Make misconfiguration detectable early.

Validation evidence to record:
- config parity checklist,
- startup log excerpt showing aligned settings,
- no secret leakage in logs.

Gate B:
- User approves security/config consistency results before moving to Big step 3.

## Big step 3: Deterministic analytics fallback and cache contract

### Task 3.1: Audit fallback logic in analytics services
- Identify fallback decision points (Trino -> Postgres or cached responses).
- Ensure deterministic behavior and explicit reason codes for fallback.

### Task 3.2: Implement cache contract and invalidation hooks
- Define concrete cache keys by org + endpoint + parameter window.
- Replace placeholder invalidation with real calls after prediction and retrain completion.
- Ensure stale reads are bounded by TTL and invalidation paths.

### Task 3.3: Add observability for fallback/cache paths
- Emit structured logs/counters for:
  - fallback triggers,
  - cache hit/miss rates,
  - invalidation success/failure.

Validation evidence to record:
- fallback decision table,
- cache key/invalidation spec,
- smoke logs with hit/miss/fallback traces.

Gate C:
- User approves deterministic fallback/cache behavior before moving to Big step 4.

## Big step 4: Introduce standalone dbt service with no DAG regression

### Task 4.1: Define service contract for dbt execution
- Add standalone dbt service in compose with:
  - mounted project/profiles,
  - network access to Trino/MinIO/HMS,
  - deterministic runtime image.

### Task 4.2: Migrate Airflow dbt execution calls
- Update DAG/helper calls to execute dbt through standalone service contract.
- Keep command signatures and selector behavior unchanged.

### Task 4.3: Run equivalence validation against current pipeline
- Compare pre/post migration for:
  - dbt run/test pass rates by layer,
  - output row-count sanity for key Silver/Gold models,
  - DAG success path stability.

Validation evidence to record:
- compose service snapshot,
- updated DAG helper references,
- pre/post equivalence table.

Gate D:
- User approves standalone dbt migration outcome before moving to Big step 5.

## Big step 5: End-to-end hardening verification and release readiness

### Task 5.1: End-to-end smoke over critical user flows
- Validate flows:
  - auth -> finance mutation -> analytics read,
  - prediction refresh -> analytics endpoint freshness,
  - role-denied paths.

### Task 5.2: Data and quality sanity on key tables
- Run row-count, null-key, duplicate-key checks on critical Gold outputs.
- Confirm no tenant leakage in serving-facing datasets.

### Task 5.3: Final gate package
- Produce final Phase 3 completion package:
  - changeset summary,
  - validation evidence,
  - residual risks,
  - rollback procedure.

Validation evidence to record:
- smoke test report,
- data-quality snapshot,
- final gate checklist.

Gate E (Phase 3 completion):
- User approves final package and transition to documentation consolidation phase.

## Deliverables at end of Phase 3

- RBAC endpoint-role matrix with closure status.
- Config consistency report and startup observability notes.
- Deterministic fallback/cache specification and implementation evidence.
- Standalone dbt migration report with pre/post equivalence.
- Final Phase 3 gate decision report (pass/fail with evidence).

## Risks and mitigations

- Risk: RBAC patches break expected access for current operators.
  - Mitigation: role regression tests before merge; staged verification with admin/accountant/cashier personas.

- Risk: standalone dbt introduces networking/runtime drift.
  - Mitigation: run equivalence table and keep rollback to in-Airflow dbt path.

- Risk: cache invalidation misses cause stale analytics.
  - Mitigation: TTL + explicit invalidation hooks + observability counters.

- Risk: fallback logic hides upstream outages.
  - Mitigation: structured fallback reason logging and alert thresholds.

## Rollback strategy

- Code rollback:
  - Revert phase-scoped commits for RBAC/config/cache/dbt-service integration.

- Pipeline rollback:
  - Switch DAG dbt execution back to in-Airflow helper path.

- Data rollback:
  - Rebuild affected dbt selectors and refresh serving tables from last known good window.

## Proposed execution order and timeline

1. Big step 1 (RBAC): 0.5-1 day
2. Big step 2 (Security/config): 0.5 day
3. Big step 3 (Fallback/cache): 1 day
4. Big step 4 (Standalone dbt): 1-1.5 days
5. Big step 5 (E2E verification): 0.5 day

Total estimate: 3.5-4.5 working days, excluding user approval wait times.
