---
name: copilot-router-skill
description: >
  Flight Director (FD) Agent skill. Parses natural language user queries
  to extract satellite tracking intents, dispatches to GNC and Weather & COMM
  console agents, and aggregates responses into mission-formatted reports.
  This is the primary entry point for all user interactions.
---

# Flight Director (FD) — Co-Pilot Router Skill

## Console Designation
**Flight Director (FD)** — The central command authority for all mission operations.
Responsible for parsing user intent, orchestrating sub-console agents, and delivering
the final mission briefing to the operator.

## Trigger Conditions
Activate this skill when:
- A natural language query arrives from the user
- The query relates to satellites, orbital tracking, or sky observation
- The system needs to determine which console agents to dispatch

This skill is the **default entry point** — all user queries route through FD first.

## Intent Taxonomy

Parse user queries into one of these mission operation categories:

| Intent Code | User Pattern Examples | Dispatches To |
|------------|----------------------|--------------|
| `TRACK_PASS` | "When does ISS pass over Bengaluru?" | GNC Console + Weather & COMM |
| `SATELLITE_POSITION` | "Where is the ISS right now?" | GNC Console only |
| `VISIBILITY_CHECK` | "Can I see Hubble from London tonight?" | GNC Console + Weather & COMM |
| `HELP` | "What can you do?", "Help" | Self (return capabilities manifest) |
| `UNKNOWN` | Unrecognized or empty queries | Self (return usage guidance) |

## Parameter Extraction Protocol

From each user query, extract the following mission parameters:

### Satellite Identification
1. Match against the common alias table (see `references/intent_taxonomy.md`)
2. If no alias match, attempt CelesTrak catalog search
3. If still unresolved → return `SATELLITE_NOT_FOUND` error
4. **Fallback default**: ISS (ZARYA), NORAD ID 25544

### Observer Location
1. Attempt geocoding via Open-Meteo Geocoding API
2. If city name unresolvable → return `LOCATION_NOT_FOUND` error
3. **Fallback default**: Bengaluru, India (12.9716°N, 77.5946°E)

### Time Window
| User Expression | Resolved Window |
|----------------|----------------|
| "tonight" | Sunset to sunrise (local time) |
| "tomorrow" | Next 24 hours from midnight local |
| "this week" | Next 168 hours |
| "next N days" | Next N × 24 hours |
| _(unspecified)_ | **Default: 72 hours** |

## Dispatch Sequence

```
1. Parse intent + extract parameters
2. Validate inputs (R-007)
3. IF intent requires orbital data:
   └─ Dispatch to GNC Console Agent (satellite-tracker-skill)
4. IF intent requires weather/visibility assessment:
   └─ Dispatch to Weather & COMM Console Agent (weather-validator-skill)
5. Await sub-console responses
6. Aggregate into Mission Briefing format
7. Run QA validation (qa-evaluator-skill)
8. Deliver final report to operator
```

## Response Aggregation — Mission Briefing Format

Combine sub-console responses into a structured report:

```
╔══════════════════════════════════════════════════════╗
║           SPACE OPERATIONS — MISSION BRIEFING        ║
╠══════════════════════════════════════════════════════╣
║ Target:    ISS (ZARYA) [NORAD 25544]                ║
║ Observer:  Bengaluru, India (12.97°N, 77.59°E)      ║
║ Window:    72 hours from 2026-07-01T09:30:00Z       ║
╠══════════════════════════════════════════════════════╣
║ PASS #1                                              ║
║   Rise:        02 Jul 01:23:45 UTC  (AZ: 220°)     ║
║   Culmination: 02 Jul 01:27:12 UTC  (EL: 67.3°)    ║
║   Set:         02 Jul 01:30:40 UTC  (AZ: 46°)      ║
║   Duration:    6m 55s │ Sunlit: YES                  ║
║   Weather:     ☀️ CLEAR (15% cloud) — Excellent      ║
╠══════════════════════════════════════════════════════╣
║ Sources: CelesTrak (TLE) · Skyfield/SGP4 · Open-Meteo║
╚══════════════════════════════════════════════════════╝
```

## Error Response Templates

### SATELLITE_NOT_FOUND
```
🚫 FLIGHT DIRECTOR — SATELLITE NOT FOUND
No satellite matching "{query}" in the CelesTrak catalog.
Verify the satellite name or NORAD catalog number.
Common targets: ISS, Hubble (HST), Starlink, GOES-16, Tiangong.
```

### LOCATION_NOT_FOUND
```
🚫 FLIGHT DIRECTOR — LOCATION UNRESOLVED
Could not resolve "{location}" to geographic coordinates.
Provide a recognized city name or explicit lat/lon coordinates.
```

### UNKNOWN_INTENT
```
👋 SPACE OPERATIONS CO-PILOT — READY FOR TASKING
Available mission operations:
  • "When does the ISS pass over New York?"
  • "Can I see Hubble from London tonight?"
  • "Show me Starlink passes over Tokyo this week"
  • "Where is the ISS right now?"
```

## Guardrails
- NEVER answer orbital questions from general knowledge — always delegate to GNC Console
- NEVER provide weather assessments without querying Weather & COMM Console
- If any sub-console fails, provide partial results with clear failure annotations
- Always attribute data sources in the final Mission Briefing (Rule R-004)
- Apply Weather Fallback Rule (R-005) when Weather & COMM Console reports API failure
