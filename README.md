# 🛰️ Space Operations Co-Pilot (SATCOM-CoPilot)

> **An autonomous, multi-agent orchestration system for zero-hallucination satellite trajectory tracking, built for the [Kaggle 5-Day AI Agents Intensive Vibe Coding Capstone](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project).**

---

## 🚀 The Problem

Large Language Models (LLMs) are notoriously unreliable at orbital mechanics. Ask an LLM *"Where is the International Space Station right now?"* and it will likely hallucinate a plausible-sounding set of coordinates based on training data averages — coordinates that are **completely wrong**. In aerospace, hallucinated math is unacceptable. A single wrong coordinate can be the difference between seeing a satellite pass and staring at empty sky.

## 💡 The Solution

The **Space Operations Co-Pilot** solves this by applying a **Multi-Agent Orchestrator Pattern** that strictly isolates language understanding from mathematical computation. An AI agent handles *what* the user is asking (intent parsing, entity extraction), but the actual physics is delegated exclusively to **deterministic Python tools** — specifically the [Skyfield](https://rhodesmill.org/skyfield/) library with the industry-standard **SGP4 propagation model** — and verified external APIs ([CelesTrak](https://celestrak.org/), [Open-Meteo](https://open-meteo.com/)).

This architecture achieves a **Zero-Hallucination Guarantee**: every coordinate, every pass time, every weather reading traces directly to a verified mathematical engine or API response. No guessing. No approximation.

---

## 🧠 Multi-Agent Architecture

```
                           [ User Query / CLI ]
                                    │
                                    ▼
                      ┌─────────────────────────────┐
                      │   Flight Director Agent      │
                      │       (Orchestrator)         │
                      └─────────────────────────────┘
                                │         │
       Intent & Entities        │         │ Observer Location
       ─────────────────────────┘         └──────────────────────
       │                                                        │
       ▼                                                        ▼
┌───────────────────────┐                          ┌──────────────────────────┐
│  GNC Console Agent    │                          │ Weather & COMM Console   │
│  (Orbital Mechanics)  │                          │  (Environmental Checks)  │
└───────────────────────┘                          └──────────────────────────┘
       │                                                        │
       │ CelesTrak TLE API                                      │ Open-Meteo API
       ▼                                                        ▼
┌───────────────────────┐                          ┌──────────────────────────┐
│ Skyfield & SGP4 Math  │                          │ Layered Cloud Analyzer   │
│      Propagator       │                          │ (Rule R-005 Fallbacks)   │
└───────────────────────┘                          └──────────────────────────┘
       │
       │ Telemetry Data
       ▼
┌───────────────────────┐
│  Folium Dashboard     │        ┌─────────────────────────────┐
│ (Live Fleet Tracking) │        │  QA / Evaluation Agent      │
└───────────────────────┘        │  (Schema & Guardrail Checks)│
                                 └─────────────────────────────┘
```

### Agent Responsibility Matrix

| Agent | Role | Tools & APIs | Skill File |
|:---|:---|:---|:---|
| **Flight Director** | Intent routing, entity extraction, response aggregation | `geocoder.py`, `map_generator.py` | `.agents/skills/copilot-router-skill/` |
| **GNC Console** | Deterministic orbital physics (SGP4 propagation) | `skyfield`, `sgp4`, CelesTrak API | `.agents/skills/satellite-tracker-skill/` |
| **Weather & COMM Console** | Atmospheric assessment, layered cloud analysis | Open-Meteo API, `visibility_classifier.py` | `.agents/skills/weather-validator-skill/` |
| **QA / Evaluation Agent** | Schema validation, hallucination detection, rubric scoring | `behave`, `pytest` | `.agents/skills/qa-evaluator-skill/` |

---

## 🎓 Kaggle Course Concepts Demonstrated

This project demonstrates **4 out of 6** key concepts from the AI Agents Intensive:

### 1. Agent / Multi-Agent System (Code)
We implemented a **hierarchical Router/Worker agent topology** with 4 specialized agents. The Flight Director orchestrates the pipeline by parsing intents (`TRACK_PASS`, `SATELLITE_POSITION`, `VISUALIZE_MAP`, `VISIBILITY_CHECK`) and delegating to domain-specific worker agents.

**Where to find it:**
- [`src/agents/orchestrator.py`](src/agents/orchestrator.py) — Flight Director with intent classification and entity extraction
- [`src/agents/space_mechanics.py`](src/agents/space_mechanics.py) — GNC Console with Skyfield/SGP4 tool calls
- [`src/agents/environmental.py`](src/agents/environmental.py) — Weather Console with Open-Meteo integration

### 2. Agent Skills (Code)
We built **custom Agent Skills** using the `.agents/skills/` convention with structured `SKILL.md` files containing YAML frontmatter, detailed execution protocols, and reference documentation:

| Skill | Location | What it defines |
|:---|:---|:---|
| `copilot-router-skill` | [`.agents/skills/copilot-router-skill/SKILL.md`](.agents/skills/copilot-router-skill/SKILL.md) | Intent taxonomy, dispatch sequences, Mission Briefing format templates |
| `satellite-tracker-skill` | [`.agents/skills/satellite-tracker-skill/SKILL.md`](.agents/skills/satellite-tracker-skill/SKILL.md) | TLE fetch protocol, SGP4 computation steps, CelesTrak API specs |
| `weather-validator-skill` | [`.agents/skills/weather-validator-skill/SKILL.md`](.agents/skills/weather-validator-skill/SKILL.md) | Open-Meteo API specs, layered cloud algorithm, fallback rules |
| `qa-evaluator-skill` | [`.agents/skills/qa-evaluator-skill/SKILL.md`](.agents/skills/qa-evaluator-skill/SKILL.md) | Scoring rubric, hallucination detection checklist, evaluation suite |

**Global Rules** are defined in [`.agents/AGENTS.md`](.agents/AGENTS.md) — 8 inviolable system-wide guardrail rules (R-001 through R-008) that all agents must follow.

### 3. Security Features (Code)
We implemented strict guardrails to prevent hallucination and ensure graceful degradation:

- **Rule R-001 (No Hallucinated Orbital Data):** All orbital data must trace to CelesTrak → SGP4. If CelesTrak is unreachable, return `DATA_SOURCE_UNAVAILABLE` — never approximate.
- **Rule R-005 (Weather Fallback):** If the Open-Meteo API fails, assume "Clear Sky", log a telemetry warning, and continue the pipeline. Never crash.
- **Rule R-007 (Input Validation):** All user inputs are validated before API dispatch (lat ∈ [-90, 90], lon ∈ [-180, 180], time window ≤ 168h).

**Where to find it:**
- [`src/config/guardrails.py`](src/config/guardrails.py) — Input validation functions
- [`features/error_handling.feature`](features/error_handling.feature) — BDD scenarios testing all failure modes

### 4. Antigravity / Vibe Coding (Video)
The entire project was built using **Spec-Driven Development** with the Antigravity CLI. We wrote BDD specifications *first*, then used Vibe Coding to iteratively implement the agent logic, tools, and UI.

---

## 🛠️ Technology Stack

| Category | Technology |
|:---|:---|
| **Language** | Python 3.10+ |
| **Agent Framework** | Antigravity CLI (Vibe Coding) |
| **Orbital Mechanics** | `skyfield`, `sgp4` |
| **Satellite Data** | CelesTrak GP Data API (TLE format) |
| **Weather Data** | Open-Meteo Free API (no key required) |
| **Geocoding** | Open-Meteo Geocoding API |
| **CLI Interface** | `typer`, `rich` (ASCII tables, pixel-art logo, color gradients) |
| **Map Visualization** | `folium` (Leaflet.js) with 20s auto-refresh fleet tracking |
| **BDD Testing** | `behave` (Gherkin framework) |
| **Unit Testing** | `pytest` |
| **Data Models** | `pydantic` v2 |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/SATTELITE_Tracking.git
cd SATTELITE_Tracking
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Co-Pilot (Interactive Mode)
```bash
# On Windows, enable UTF-8 encoding first:
$env:PYTHONUTF8=1

# Launch the interactive CLI:
python -m src.main
```

### 4. Run in Single-Shot Mode
```bash
python -m src.main "Where is the ISS right now?"
python -m src.main "When does Hubble pass over London?"
python -m src.main "Show me the ISS and Hubble on a map"
```

---

## 🧪 Testing & Validation

### BDD Tests (Gherkin)
```bash
behave features/
```

Our test suite includes:
- **16 end-to-end integration scenarios**
- **152 verified execution steps**
- **100% pass rate** across all validation matrices
- Deterministic JSON/TLE fixtures (no live network dependency)

### Test Coverage

| Feature File | Scenarios | What it Tests |
|:---|:---|:---|
| `satellite_tracking.feature` | 6 | TLE fetch, SGP4 computation, pass window validation |
| `weather_validation.feature` | 5 | Cloud layer analysis, visibility classification, R-005 fallback |
| `error_handling.feature` | 5 | Invalid inputs, API failures, graceful degradation |

---

## 📁 Project Structure

```
SATTELITE_Tracking/
├── .agents/                         # Agent Skills & Global Rules
│   ├── AGENTS.md                    # Global guardrail rules (R-001 → R-008)
│   └── skills/
│       ├── copilot-router-skill/    # Flight Director skill + references
│       ├── satellite-tracker-skill/ # GNC Console skill + TLE specs + examples
│       ├── weather-validator-skill/ # Weather Console skill + API docs + examples
│       └── qa-evaluator-skill/      # QA Agent skill + rubric criteria
│
├── src/                             # Core Application
│   ├── main.py                      # Typer/Rich CLI with pixel-art logo
│   ├── agents/
│   │   ├── orchestrator.py          # Flight Director (intent routing)
│   │   ├── space_mechanics.py       # GNC Console (orbital physics)
│   │   ├── environmental.py         # Weather Console (cloud analysis)
│   │   └── qa_evaluator.py          # QA Agent (schema validation)
│   ├── tools/
│   │   ├── tle_fetcher.py           # CelesTrak API client
│   │   ├── pass_calculator.py       # Skyfield/SGP4 propagation
│   │   ├── weather_fetcher.py       # Open-Meteo API client
│   │   ├── visibility_classifier.py # Layered cloud algorithm
│   │   ├── geocoder.py              # City → coordinates resolver
│   │   └── map_generator.py         # Folium fleet tracking maps
│   ├── models/                      # Pydantic v2 data schemas
│   └── config/                      # Settings & guardrails
│
├── features/                        # BDD Test Specifications (Gherkin)
│   ├── satellite_tracking.feature
│   ├── weather_validation.feature
│   ├── error_handling.feature
│   └── steps/                       # Step definition implementations
│
├── evaluations/                     # QA Evaluation Suite
│   ├── eval_config.yaml             # Evaluation configuration
│   ├── datasets/                    # Ground-truth test data
│   └── rubrics/                     # Scoring rubrics (accuracy, guardrails, completeness)
│
└── tests/                           # Unit & Integration Tests
    └── fixtures/                    # Mock TLE & weather JSON data
```

---

## 📜 License

This project was built as a submission for the Kaggle 5-Day AI Agents Intensive Vibe Coding Capstone Project.
