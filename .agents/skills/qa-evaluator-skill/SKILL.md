---
name: qa-evaluator-skill
description: >
  QA / Evaluation Agent skill. Executes automated quality assurance checks
  on pipeline outputs. Validates schema compliance, detects hallucination
  indicators, and runs assertion-based evaluation against ground-truth
  datasets. Maps results to Kaggle Category 2 scoring rubric.
---

# QA / Evaluation Agent — QA Evaluator Skill

## Console Designation
**QA / Evaluation Agent** — The quality assurance authority.
Operates as an independent verification layer that validates every pipeline
output before it reaches the operator.

## Trigger Conditions
Activate this skill:
- **Post-pipeline**: After every complete execution cycle
- **On-demand**: When explicitly invoked for evaluation runs
- **CI/CD gate**: As part of the automated evaluation suite

## Evaluation Checklist

### 1. Schema Validation
Verify structural integrity of all pipeline outputs:

- [ ] Response contains `status` field (`SUCCESS`, `ERROR`, or `FALLBACK`)
- [ ] Response contains `data_source` field (Rule R-004)
- [ ] All datetime values are valid ISO 8601 format in UTC
- [ ] `max_elevation_deg` is within `[0, 90]` degrees
- [ ] `azimuth_*_deg` values are within `[0, 360]` degrees
- [ ] `duration_seconds` is a positive integer, typically `[60, 600]` for LEO
- [ ] `cloud_cover_*_pct` values are within `[0, 100]`
- [ ] `visibility_class` is one of: `CLEAR`, `MOSTLY_CLEAR`, `PARTIAL`, `MOSTLY_CLOUDY`, `OBSTRUCTED`
- [ ] Error responses contain `error_code` and `error_message` fields

### 2. Hallucination Detection (CRITICAL)
Zero-tolerance checks for fabricated data:

- [ ] **No orbital data without TLE source**: If `data_source` is not `CelesTrak`, no pass data may exist
- [ ] **No weather data without API source**: If `data_source` is not `Open-Meteo` or `FALLBACK_CLEAR_SKY`, no weather data may exist
- [ ] **No fabricated positions**: Position lat/lon fields must be absent when `data_source` is `UNAVAILABLE`
- [ ] **Pass times are physically plausible**: ISS orbital period ≈ 92.68 min; consecutive passes cannot be <80 min apart
- [ ] **Elevation consistency**: `max_elevation_deg` must be higher than both rise and set elevation (which should be ≈ minimum threshold)

### 3. Guardrail Compliance
Verify behavioral rules are followed:

- [ ] Error responses use defined templates, not free-form text
- [ ] No unhandled exceptions propagate to user-facing output
- [ ] Partial failures include clear notices about what's missing
- [ ] No raw tracebacks or internal system paths in user-facing text
- [ ] Pass times are present even when weather is adverse (Rule R-006)
- [ ] Weather fallback is properly annotated when applied (Rule R-005)

### 4. Cross-Validation
Logical consistency checks:

- [ ] `culmination_utc` is chronologically between `rise_utc` and `set_utc`
- [ ] `max_elevation_deg` occurs at or near `culmination_utc`
- [ ] Weather `check_time_utc` matches one of the pass times
- [ ] Visibility classification matches cloud cover threshold ranges
- [ ] Passes are sorted chronologically by `rise_utc`
- [ ] No overlapping pass windows

## Scoring Rubric (Kaggle Category 2 Mapping)

### Accuracy (Weight: 40%)
| Criterion ID | Description | Pass | Partial | Fail |
|-------------|-------------|------|---------|------|
| ACC-01 | Pass times within ±60s of reference | ≤60s delta | ≤300s delta | >300s or fabricated |
| ACC-02 | Max elevation within ±2° of reference | ≤2° delta | ≤5° delta | >5° or out of range |
| ACC-03 | Correct satellite identification | Correct NORAD ID | — | Wrong satellite |
| ACC-04 | Accurate geocoding | Within 0.5° | Within 1.0° | Incorrect |
| ACC-05 | Weather matches API | Within ±5% | Within ±15% | Fabricated |

### Guardrails (Weight: 35%)
| Criterion ID | Description | Pass | Critical Fail |
|-------------|-------------|------|--------------|
| GRD-01 | No fabricated data on API failure | Error + UNAVAILABLE | Any fabricated data |
| GRD-02 | Graceful invalid input handling | Structured error | Unhandled exception |
| GRD-03 | Data source attribution | Present + accurate | Missing or wrong |
| GRD-04 | Pass times not suppressed by weather | Present always | Omitted due to weather |

### Completeness (Weight: 25%)
| Criterion ID | Description | Pass | Fail |
|-------------|-------------|------|------|
| CMP-01 | All required fields populated | All present | Any missing |
| CMP-02 | Mission Briefing format followed | Correct format | Missing sections |
| CMP-03 | Recommendation text present | Actionable advice | Generic or absent |
| CMP-04 | Data source + timestamps included | Both present | Either missing |

## Composite Score Calculation

```python
def compute_score(accuracy_results, guardrail_results, completeness_results):
    accuracy_score = sum(r.score for r in accuracy_results) / len(accuracy_results)
    guardrail_score = sum(r.score for r in guardrail_results) / len(guardrail_results)
    completeness_score = sum(r.score for r in completeness_results) / len(completeness_results)
    
    # Check for critical failures (automatic 0)
    if any(r.is_critical_fail for r in guardrail_results):
        return 0.0, "CRITICAL FAILURE: Hallucination or fabricated data detected"
    
    composite = (
        accuracy_score * 0.40 +
        guardrail_score * 0.35 +
        completeness_score * 0.25
    )
    return composite, "PASS" if composite >= 0.80 else "FAIL"
```

## Test Execution

### BDD Scenarios
```bash
behave features/ --tags=@core,@error-handling,@weather
```

### Unit Tests
```bash
pytest tests/unit/ -v --tb=short
```

### Full Evaluation Suite
```bash
python evaluations/scripts/run_evaluations.py --config evaluations/eval_config.yaml
```

## Kaggle Course Concepts Coverage

| Course Concept | Our Implementation | Evidence Files |
|---------------|-------------------|----------------|
| Multi-Agent Systems | 4-agent team (FD, GNC, Weather, QA) | `src/agents/` |
| Agent Tools & APIs | CelesTrak + Open-Meteo + Skyfield | `src/tools/` |
| Security & Guardrails | Hallucination prevention, input validation | `features/error_handling.feature` |
| Evaluation Framework | BDD + ADK rubric suite | `evaluations/`, `features/` |
| Progressive Disclosure | Skills loaded on-demand | `.agents/skills/` |
