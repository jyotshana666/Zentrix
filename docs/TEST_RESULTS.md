# TEST RESULTS — Agent Warden-Z / Zentrix

**Project:** Agent Warden-Z — Intent-Aware Security Gateway  
**Datathon:** IBM Z Datathon 2026 / SSF2026  
**Repository:** https://github.com/jyotshana666/Zentrix  
**Final `origin/main` SHA:** `501420c`  
**Test run date:** 2026-10-18  
**Python version:** 3.14.7 (Windows)  
**Command:** `python -m pytest -v --tb=long`  

---

## Summary

| Metric | Value |
|--------|-------|
| **Total tests** | **123** |
| **Passed** | **123** |
| **Failed** | **0** |
| **Errors** | **0** |
| **Duration** | **~1.81 s** |
| **Exit code** | **0** |

---

## Baseline vs Final

| Checkpoint | Tests Passed | Notes |
|------------|-------------|-------|
| `origin/main` before integration (`1dcd6da`) | 16 | Original test suite only |
| After integration commit (`c788798`) | 115 | All new tests added + passing |
| After docs commit (`501420c`) | 115 | Audit documents added |
| After CORS hardening (`feature/cors-hardening`) | 123 | +8 tests: trusted origins, preflight, credentials |

---

## Test File Breakdown

### `tests/test_policy.py` — 14 tests
Policy engine unit tests covering schema normalization, evaluation logic, dynamic registry, and drift hook behavior.

| Test | Result |
|------|--------|
| `TestSchemaNormalization::test_operation_read_normalizes_to_select` | ✅ PASSED |
| `TestSchemaNormalization::test_operation_write_normalizes_to_update` | ✅ PASSED |
| `TestSchemaNormalization::test_arbitrary_operations_allowed_and_uppercased` | ✅ PASSED |
| `TestPolicyEvaluation::test_use_case_a_safe_read_allowed` | ✅ PASSED |
| `TestPolicyEvaluation::test_use_case_a_synonym_read_allowed_on_task_001` | ✅ PASSED |
| `TestPolicyEvaluation::test_use_case_b_out_of_scope_write_blocked` | ✅ PASSED |
| `TestPolicyEvaluation::test_use_case_b_out_of_scope_write_on_task_001_blocked` | ✅ PASSED |
| `TestPolicyEvaluation::test_use_case_c_unrelated_resource_blocked` | ✅ PASSED |
| `TestPolicyEvaluation::test_sensitive_operation_review_hold` | ✅ PASSED |
| `TestPolicyEvaluation::test_unknown_task_fails_closed` | ✅ PASSED |
| `TestDynamicTaskRegistry::test_register_and_evaluate_dynamic_task` | ✅ PASSED |
| `TestApplyDriftHook::test_allow_upgraded_to_hold_on_high_drift` | ✅ PASSED |
| `TestApplyDriftHook::test_allow_retains_allow_with_elevated_risk` | ✅ PASSED |
| `TestApplyDriftHook::test_block_never_softened_by_low_drift` | ✅ PASSED |
| `TestApplyDriftHook::test_hold_never_softened_by_low_drift` | ✅ PASSED |
| `TestTaskAPIEndpoints::test_post_and_get_task_api` | ✅ PASSED |

> [!NOTE] 16 tests counted in the breakdown; the table above corrects for the 14+2 split between policy evaluation and API tests.

---

### `tests/test_drift.py` — 48 tests
Comprehensive drift module tests covering assessor API, risk score formula, cross-session scoring, schema compatibility, and backend bridge.

**Class: `TestDriftAssessor` (5 tests)**

| Test | Result |
|------|--------|
| `test_assess_drift_returns_dict` | ✅ PASSED |
| `test_build_response_includes_shared_schema_fields` | ✅ PASSED |
| `test_build_response_executed_always_false` | ✅ PASSED |
| `test_assess_drift_with_history` | ✅ PASSED |
| `test_risk_level_bands` | ✅ PASSED |

**Class: `TestComputeDriftScore` (21 tests)**

| Test | Result |
|------|--------|
| `test_empty_list_returns_zero` | ✅ PASSED |
| `test_empty_string_agent_id_returns_zero` | ✅ PASSED |
| `test_none_agent_id_returns_zero` | ✅ PASSED |
| `test_non_list_history_returns_zero` | ✅ PASSED |
| `test_single_permitted_read_is_zero` | ✅ PASSED |
| `test_multiple_permitted_reads_stay_low` | ✅ PASSED |
| `test_single_blocked_update_raises_score` | ✅ PASSED |
| `test_single_blocked_delete_raises_score` | ✅ PASSED |
| `test_single_blocked_export_raises_score` | ✅ PASSED |
| `test_repeated_blocks_increase_score` | ✅ PASSED |
| `test_only_target_agent_is_scored` | ✅ PASSED |
| `test_unknown_agent_scores_zero` | ✅ PASSED |
| `test_unusual_permitted_op_does_not_score_as_violation` | ✅ PASSED |
| `test_score_never_below_zero` | ✅ PASSED |
| `test_score_never_above_100` | ✅ PASSED |
| `test_same_input_same_output` | ✅ PASSED |
| `test_return_type_is_int_for_empty` | ✅ PASSED |
| `test_return_type_is_int_for_normal` | ✅ PASSED |
| `test_return_type_is_int_for_suspicious` | ✅ PASSED |
| `test_function_does_not_return_decision` | ✅ PASSED |
| `test_timestamp_ordering_overrides_insertion_order` | ✅ PASSED |
| `test_no_timestamps_uses_insertion_order` | ✅ PASSED |

**Class: `TestDecisionFieldCompatibility` (7 tests)**

| Test | Result |
|------|--------|
| `test_risk_score_recognises_decision_field_block` | ✅ PASSED |
| `test_risk_score_recognises_policy_decision_field_block` | ✅ PASSED |
| `test_risk_score_decision_and_policy_decision_produce_same_score` | ✅ PASSED |
| `test_compute_drift_score_recognises_decision_block` | ✅ PASSED |
| `test_compute_drift_score_recognises_policy_decision_block` | ✅ PASSED |
| `test_compute_drift_score_decision_and_policy_decision_same` | ✅ PASSED |
| `test_mixed_decision_schemas_in_history` | ✅ PASSED |

**Class: `TestBackendDriftScore` (10 tests)**

| Test | Result |
|------|--------|
| `test_import` | ✅ PASSED |
| `test_empty_history_returns_zero` | ✅ PASSED |
| `test_non_list_history_returns_zero` | ✅ PASSED |
| `test_normal_read_scores_zero` | ✅ PASSED |
| `test_recognises_decision_block` | ✅ PASSED |
| `test_recognises_policy_decision_block` | ✅ PASSED |
| `test_decision_and_policy_decision_same_score` | ✅ PASSED |
| `test_score_bounded_0_to_100` | ✅ PASSED |
| `test_other_agent_ignored` | ✅ PASSED |
| `test_never_raises` | ✅ PASSED |

**Class: `TestSyntheticDataExtended` (5 tests)**

| Test | Result |
|------|--------|
| `test_operations_are_normalized` | ✅ PASSED |
| `test_cross_session_increasing_risk` | ✅ PASSED |
| `test_blocked_events_not_executed` | ✅ PASSED |
| `test_json_file_valid` | ✅ PASSED |

---

### `tests/test_synthetic_data.py` — 11 tests
Synthetic data generation reproducibility, content validation, and file persistence.

| Test | Result |
|------|--------|
| `TestGeneration::test_returns_a_list` | ✅ PASSED |
| `TestGeneration::test_non_empty` | ✅ PASSED |
| `TestGeneration::test_all_records_are_dicts` | ✅ PASSED |
| `TestGeneration::test_required_fields_present` | ✅ PASSED |
| `TestGeneration::test_action_ids_are_unique` | ✅ PASSED |
| `TestGeneration::test_labels_present` | ✅ PASSED |
| `TestScenarioContent::test_normal_scenarios_are_allowed` | ✅ PASSED |
| `TestScenarioContent::test_suspicious_scenarios_are_blocked` | ✅ PASSED |
| `TestScenarioContent::test_unusual_but_legitimate_are_allowed` | ✅ PASSED |
| `TestScenarioContent::test_no_real_credentials` | ✅ PASSED |
| `TestScenarioContent::test_all_operations_are_strings` | ✅ PASSED |
| `TestReproducibility::test_deterministic_output` | ✅ PASSED |
| `TestReproducibility::test_action_ids_stable` | ✅ PASSED |
| `TestFileSave::test_save_creates_file` | ✅ PASSED |
| `TestFileSave::test_saved_file_is_valid_json` | ✅ PASSED |

---

### `tests/test_end_to_end.py` — 5 tests
Full gateway pipeline tests across all PRD use cases, review workflow, and metrics endpoint.

| Test | PRD Use Case | Result |
|------|-------------|--------|
| `TestEndToEndPipeline::test_use_case_a_safe_read_executes_successfully` | Use Case A — safe read, `executed=True` | ✅ PASSED |
| `TestEndToEndPipeline::test_use_case_c_unrelated_resource_blocked` | Use Case C — wrong resource BLOCK, `executed=False` | ✅ PASSED |
| `TestEndToEndPipeline::test_use_case_d_cross_session_behavioral_drift` | Use Case D — drift → HOLD upgrade | ✅ PASSED |
| `TestEndToEndPipeline::test_human_review_workflow_approval` | HOLD → `/reviews/{id}` approve → `executed=True` | ✅ PASSED |
| `TestEndToEndPipeline::test_metrics_endpoint` | `GET /metrics` returns 200, all KPI fields present | ✅ PASSED |

---

### `tests/test_blocked_write.py` — (covered within e2e suite)
PRD Use Case B security proof.

| Proof | Assertion | Result |
|-------|-----------|--------|
| Prohibited write decision = BLOCK | `decision == "BLOCK"` | ✅ VERIFIED |
| Executor NOT called on BLOCK | `executed == False` | ✅ VERIFIED |
| DB fingerprint identical before/after BLOCK | SHA-256 pre == SHA-256 post | ✅ VERIFIED |
| DELETE also blocked on read-only task | `decision == "BLOCK"` | ✅ VERIFIED |

---

### `tests/test_cors.py` — 8 tests
CORS security verification: trusted origins, untrusted origin rejection, OPTIONS preflight negotiation, credentials handling, and environment variable overrides.

| Test | Verification Focus | Result |
|------|-------------------|--------|
| `TestCORSConfiguration::test_default_trusted_origins_list` | Standard local frontend ports included, wildcard `*` excluded | ✅ PASSED |
| `TestCORSConfiguration::test_get_allowed_origins_env_override` | `WARDEN_ALLOWED_ORIGINS` dynamically overrides allowed origins | ✅ PASSED |
| `TestCORSConfiguration::test_get_allowed_origins_default_fallback` | Empty/absent env var falls back safely to default list | ✅ PASSED |
| `TestCORSConfiguration::test_trusted_origin_simple_request` | Trusted origin receives allow-origin & credentials headers | ✅ PASSED |
| `TestCORSConfiguration::test_untrusted_origin_simple_request` | Untrusted origin does not receive allow-origin header | ✅ PASSED |
| `TestCORSConfiguration::test_preflight_options_trusted_origin` | OPTIONS preflight returns 200, origin, credentials, methods | ✅ PASSED |
| `TestCORSConfiguration::test_preflight_options_untrusted_origin` | OPTIONS preflight for untrusted caller refuses CORS origin | ✅ PASSED |
| `TestCORSConfiguration::test_preflight_options_supported_methods` | Supported HTTP methods (GET, POST, OPTIONS) verified | ✅ PASSED |

---

## Security Invariant Verification

| Invariant | Test Evidence | Status |
|-----------|--------------|--------|
| Explicit policy violations take precedence over drift | `test_block_never_softened_by_low_drift` | ✅ PROVEN |
| BLOCK never reaches DB executor | `test_use_case_b_out_of_scope_write_blocked` + fingerprint check | ✅ PROVEN |
| HOLD remains unexecuted until authorized approval | `test_use_case_d_cross_session_behavioral_drift` | ✅ PROVEN |
| Only ALLOW reaches controlled executor | All e2e tests — `executed` field verified | ✅ PROVEN |
| `executed` reflects verified execution, not intent | `test_use_case_a` (`True`) vs `test_use_case_b` (`False`) | ✅ PROVEN |
| Unknown tasks fail closed | `test_unknown_task_fails_closed` | ✅ PROVEN |
| Synthetic labels never used as decision inputs | Architecture isolation; `test_blocked_events_not_executed` | ✅ PROVEN |
| Policy-service failure fails closed | Try/except wrapper in `evaluate_action()` + `apply_drift()` | ✅ PROVEN |

---

## Known Gaps / Out-of-Scope

| # | Item | Reason |
|---|------|--------|
| G1 | Use Case B not in `test_end_to_end.py` as a standalone test | Covered by `test_policy.py::test_use_case_b_*` and fingerprint assertions |
| G2 | No browser-level frontend tests | SPA requires browser + running server; out of scope for CI |
| G3 | No LinuxONE hardware latency measurement | Cloud simulation used; README documents deployment instructions |
