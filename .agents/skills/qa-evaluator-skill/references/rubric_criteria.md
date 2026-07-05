# Kaggle Category 2 — Scoring Rubric Mapping

## Category 2: Technical Implementation & Validation

### Required: Demonstrate ≥3 Key Concepts from the Intensive Course

| # | Course Concept | Our Implementation | Score Target |
|---|---------------|-------------------|-------------|
| 1 | **Multi-Agent Systems** | 4-agent team: Flight Director (FD), GNC Console, Weather & COMM Console, QA Agent. Hierarchical dispatch with message contracts. | ✅ Full marks |
| 2 | **Agent Tools & Interoperability** | CelesTrak API (TLE data), Open-Meteo API (weather), Skyfield/SGP4 (computation). MCP-compatible tool definitions. | ✅ Full marks |
| 3 | **Security & Evaluation** | Guardrail rules (R-001 through R-008), hallucination prevention, BDD test suite, ADK evaluation rubrics. | ✅ Full marks |
| 4 | **Agent Skills & Memory** | Progressive-disclosure SKILL.md files, TLE caching (4-hour TTL), satellite alias memory. | ✅ Full marks (bonus) |

> We implement **4 out of 4** concepts (exceeding the minimum of 3).

### Code Quality Assessment

| Criterion | Evidence | Location |
|-----------|---------|----------|
| Functional code | All tools produce verified outputs | `src/tools/` |
| Clean architecture | Separation of agents, tools, models | `src/agents/`, `src/tools/`, `src/models/` |
| Documentation | SKILL.md files, API references, architecture docs | `.agents/skills/`, `docs/` |
| Error handling | 5 Gherkin error scenarios | `features/error_handling.feature` |

### Architecture Clarity

| Element | Evidence |
|---------|---------|
| Agent topology diagram | Mermaid diagram in architecture docs |
| Data flow documentation | Message contract JSON schemas |
| Sequential vs hierarchical | Hierarchical: FD dispatches to GNC + Weather |
| Tool binding | Each agent loads specific SKILL.md on demand |

### Technical Robustness

| Evidence Type | Location | Description |
|--------------|----------|-------------|
| Agent reasoning traces | `evaluations/reports/` | Logged decision paths |
| API response logs | Captured in evaluation runs | Raw CelesTrak + Open-Meteo responses |
| Test results | `behave` + `pytest` output | Pass/fail for all scenarios |
| Mock-based determinism | `tests/fixtures/` | Hardcoded TLE + weather mocks |

---

## Scoring Breakdown (Target: Maximum Points)

### Accuracy Rubric (40% weight)
- ACC-01: Pass time accuracy (±60s) → validates SGP4 computation
- ACC-02: Elevation accuracy (±2°) → validates topocentric transform
- ACC-03: Satellite identification → validates alias resolution
- ACC-04: Geocoding accuracy → validates Open-Meteo geocoding
- ACC-05: Weather data fidelity → validates API response parsing

### Guardrails Rubric (35% weight)
- GRD-01: Zero fabricated data on API failure (CRITICAL)
- GRD-02: Graceful error handling for all invalid inputs
- GRD-03: Data source attribution on every response
- GRD-04: Pass times never suppressed by weather

### Completeness Rubric (25% weight)
- CMP-01: All required fields populated in success responses
- CMP-02: Mission Briefing format consistency
- CMP-03: Actionable observation recommendations
- CMP-04: Timestamps and source metadata present

---

## Minimum Pass Threshold
- **Composite score ≥ 0.80** (80%) required to pass
- **Any critical failure** (hallucination, fabricated data) → automatic 0
