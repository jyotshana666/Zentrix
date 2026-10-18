# TEAM BRANCH PLAN — Agent Warden-Z / Zentrix

**Project:** Agent Warden-Z — Intent-Aware Security Gateway  
**Datathon:** IBM Z Datathon 2026 / SSF2026  
**Repository:** https://github.com/jyotshana666/Zentrix  
**Document created:** 2026-10-18  
**Last verified fetch:** 2026-10-18T11:47 UTC  

---

## 1. Branch-to-Member Ownership Matrix

| Branch | Member | Role | Remote HEAD SHA | Status |
|--------|--------|------|----------------|--------|
| `feature/policy-gateway` | Member 1 | Schemas, task registry, deterministic policy engine, pre-execution enforcement | `453964a` | ✅ Merged into `origin/main` |
| `feature/behavioral-drift` | Member 2 | Synthetic scenarios, history aggregation, drift scoring, explainable risk signals | `c1a6638` | ✅ Merged into local `main` via `3aa3bba`; not yet on `origin/main` |
| `feature/executor-and-audit` | Member 3 | Controlled DB execution, resource matching, DB fingerprints, audit persistence | `fa7db42` | ✅ Merged into `origin/main` |
| `feature/warden-dashboard` | Member 4 | Frontend/API integration, action history, decision explanations, risk visualization | `f24cb2a` | ✅ Merged into `origin/main` |
| `feature/hold-and-execute-hook` | Member 5 (support) | HOLD outcome, `apply_drift` hook, execute stub, held queue | `9c01361` | ✅ Merged into `origin/main` |
| `feature/wire-pipeline` | Member 5 | Wire policy engine to executor and audit log | `55ee5ae` | ✅ Merged into `origin/main` |
| `feature/demo-policies` | Member 5 (WIP) | Demo policies for datathon | `8619870` | ⚠️ Superseded by `453964a` on `origin/main`; stale WIP |

---

## 2. Per-Branch Detailed Audit (as at 2026-10-18 fetch)

### 2.1 `feature/policy-gateway` (Member 1)
- **Remote HEAD:** `453964a` — *"feat(policy): normalize operations, add dynamic task registry, calibrate demo policies"*
- **Merged into `origin/main`:** YES — this is the tip of `origin/main`'s merged chain
- **Unique commits over initial:** `93638fe` (initial policy enforcement API), `9b0ce58` (PR merge), `9c01361` (HOLD merge), `fd44d5b`, `fa7db42` (executor merge), `7e2e578`, `55ee5ae` (wire merge), `7fec45b`, `453964a`
- **Files owned:**
  - `backend/policy_engine.py` — static `TASK_POLICIES`, `evaluate_action()`, `apply_drift()`, dynamic registry functions
  - `backend/schemas.py` — `ActionRequest`, `EvaluateRequest`, `DecisionResponse`, `EvaluateResponse`
  - `tests/test_policy.py` — 14 unit tests for schema normalization, policy evaluation, dynamic registry, drift hook
- **Feature completeness:** COMPLETE (as merged into main)
- **Integration issues found:** Operation-normalization aliases (`"read"` → `"SELECT"`, `"write"` → `"UPDATE"`) added; resource prefix-matching fixed in integration work

---

### 2.2 `feature/behavioral-drift` (Member 2)
- **Remote HEAD:** `c1a6638` — *"fix(drift): unify audit decision schema and calibrate cross-session scoring"*
- **Author:** SHREYA0510006
- **Git root:** Independent (`a59b7ea`) — **no common ancestor with main's root** (`c039ec2`)
- **Merged into `origin/main`:** NO — merged only into local `main` via `3aa3bba` (5 commits ahead of `origin/main`)
- **Unique commits:**
  - `a59b7ea` — Initial commit: project README and shared schema documentation
  - `d206c71` — Implement behavioral drift scoring and synthetic data
  - `c1a6638` — fix: unify audit decision schema and calibrate cross-session scoring
- **Files added (not in `origin/main`):**
  - `drift/__init__.py`, `drift/drift_assessor.py`, `drift/generate_data.py`, `drift/risk_score.py`, `drift/session_history.py`
  - `data/synthetic_agent_actions.json` (181 synthetic records)
  - `tests/test_drift.py` (1087-line comprehensive test suite)
  - `tests/test_synthetic_data.py`
  - `tests/__init__.py`
- **Feature completeness:** COMPLETE as a standalone module; integration into gateway required `backend/drift.py` bridge
- **Security note:** Synthetic labels (`is_suspicious`, `is_legitimate`) are evaluation-only — never used as decision inputs in gateway
- **Integration risk:** Independent git root required `--allow-unrelated-histories` merge. `.gitignore` conflict resolved manually.

---

### 2.3 `feature/executor-and-audit` (Member 3)
- **Remote HEAD:** `fa7db42` — *"Add SQLite executor, audit log, db fingerprint; fix gitignore"*
- **Merged into `origin/main`:** YES
- **Files owned:**
  - `backend/database.py` — SQLite executor (`execute_action()`), `get_audit_log()`, `compute_db_fingerprint()`, `get_agent_history()`, `get_transaction()`
- **Feature completeness:** PARTIAL before integration — resource matching only supported exact lowercase `"transactions"`; fingerprint function existed but executor lacked `held_actions` table
- **Defects fixed in integration phase:**
  - Resource matching updated to support `"transaction_TX1042"` and prefix variants
  - Added `held_actions` SQLite table with full persistent review queue
  - Added `compute_system_metrics()` for real-time KPI endpoint
  - Fixed `get_transaction()` case-insensitive matching

---

### 2.4 `feature/warden-dashboard` (Member 4)
- **Remote HEAD:** `f24cb2a` — *"feat(frontend): connect Warden-Z dashboard to backend"*
- **Merged into `origin/main`:** YES
- **Files owned:**
  - `frontend/index.html` — full SPA layout (885 lines)
  - `frontend/css/style.css` — terminal/dark theme (2056 lines)
  - `frontend/js/app.js` — API client, simulation fallback, state management (1828+ lines)
- **Feature completeness:** PARTIAL before integration — 3 backend endpoints missing (`/metrics`, `/agents/{id}/risk`, `/reviews/{id}`); CORS not configured
- **Defects fixed in integration phase:**
  - Added `CORSMiddleware` with `allow_origins=["*"]` in `backend/app.py`
  - Added 3 missing backend endpoints
  - Updated `frontend/js/app.js` with `getMetrics()`, `getAgentRisk()`, `reviewAction()` client methods

---

### 2.5 `feature/hold-and-execute-hook` (Member 5 support)
- **Remote HEAD:** `9c01361` — *"Add HOLD outcome, apply_drift hook, execute stub, held queue"*
- **Merged into `origin/main`:** YES
- **Feature completeness:** PARTIAL — `apply_drift` was wired but never called from `/actions/execute`; held queue was in-memory only (lost on restart)
- **Defects fixed in integration phase:**
  - `/actions/execute` now calls `compute_drift_score()` then `apply_drift()` on every request
  - `held_actions` persisted to SQLite; in-memory list maintained for backward compatibility

---

### 2.6 `feature/wire-pipeline` (Member 5 integration)
- **Remote HEAD:** `55ee5ae` — *"Wire policy engine to executor and audit log"*
- **Merged into `origin/main`:** YES
- **Feature completeness:** PARTIAL — executor called regardless of decision (BLOCK and HOLD both hit executor); drift not wired; audit completeness not validated
- **Defects fixed in integration phase:**
  - ALLOW-only executor path enforced
  - HOLD persisted, BLOCK never touches executor
  - Drift pipeline integrated before every decision response

---

### 2.7 `feature/demo-policies` (Member 5 WIP)
- **Remote HEAD:** `8619870` — *"WIP: demo policies (untested)"*
- **Merged into `origin/main`:** Effectively NO — commit attempted to add `task_read_customer`, `task_export_report`, and `task_bulk_delete` task definitions, but `453964a` on `origin/main` already includes a more complete, tested version of `TASK_POLICIES`
- **Recommendation:** Close or abandon this branch. The WIP commit is a strict subset of what is now on `main`. Do not open a PR without first rebasing onto `main`.

---

## 3. Integration Order (Dependency Graph)

```
[Shared Schemas]  →  [Policy Gateway]  →  [HOLD Hook]
                                        ↓
                  [Executor + Audit]  →  [Wire Pipeline]  →  [Behavioral Drift Bridge]
                                                           ↓
                                              [Dashboard CORS + Endpoints]
                                                           ↓
                                              [Demo Policies + Metrics + Tests]
                                                           ↓
                                              [README + Docs + Integration Report]
```

**Merge order for PRs (actual sequence executed):**
1. PR #1 — `feature/policy-gateway` → ✅ merged
2. PR #2 — `feature/hold-and-execute-hook` → ✅ merged
3. PR #3 — `feature/executor-and-audit` → ✅ merged
4. PR #4 — `feature/wire-pipeline` → ✅ merged
5. PR #5 — `feature/warden-dashboard` → ✅ merged
6. PR #6 — `feature/behavioral-drift` → 🔲 pending (local only, needs push to `origin/main`)
7. Integration commit (`c788798`) → 🔲 pending push to `origin/main`

---

## 4. What Remains on Local `main` Not Yet on `origin/main`

Local `main` is **5 commits ahead** of `origin/main` (SHA `1dcd6da`):

| # | Commit SHA | Description |
|---|-----------|-------------|
| 5 | `c788798` | feat(integration): unify gateway pipeline, wire behavioral drift, add audit guarantees and metrics |
| 4 | `3aa3bba` | feat(drift): merge behavioral drift detection, synthetic data and test suite |
| 3 | `c1a6638` | fix(drift): unify audit decision schema (from `origin/feature/behavioral-drift`) |
| 2 | `d206c71` | Implement behavioral drift scoring and synthetic data |
| 1 | `1dcd6da` | `origin/main` HEAD (merge of `feature/warden-dashboard`) |

**Plan:** Push local `main` to `origin/main` after final verification (tests passing 115/115).

---

## 5. Team Responsibility Summary

| Member | Primary Branch | Deliverable | PRD Section | Status |
|--------|---------------|-------------|-------------|--------|
| Member 1 | `feature/policy-gateway` | TASK_POLICIES, `evaluate_action()`, schema normalization, dynamic task registry | §3.2 Policy Engine | ✅ Complete |
| Member 2 | `feature/behavioral-drift` | Drift module (`drift/`), synthetic data, risk scoring, session history | §3.3 Behavioral Drift | ✅ Complete (needs `origin/main` push) |
| Member 3 | `feature/executor-and-audit` | SQLite executor, DB fingerprint, audit log | §3.4 Controlled Executor | ✅ Complete (enhancements in integration) |
| Member 4 | `feature/warden-dashboard` | SPA dashboard, API client, CORS | §3.5 Dashboard | ✅ Complete (missing endpoints added in integration) |
| Member 5 | `feature/wire-pipeline`, `feature/hold-and-execute-hook`, `feature/demo-policies` | E2E integration, metrics, docs, tests, deployment | §3.1 Gateway, §4 Metrics | ✅ Complete |
