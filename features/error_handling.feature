@error-handling @guardrails
Feature: Graceful Error Handling & Guardrail Compliance
  As a system operator,
  I want the Co-Pilot to handle invalid inputs gracefully,
  So that users receive helpful feedback instead of crashes or hallucinations.

  Background:
    Given the Flight Director is initialized with guardrail rules R-001 through R-008
    And input validation is active for coordinates, satellite names, and time windows

  @invalid-satellite
  Scenario: Non-existent satellite name
    Given the user asks "Track satellite PHANTOM-9000 over Paris"
    When the Flight Director parses the intent as "TRACK_PASS"
    And the GNC Console searches CelesTrak for "PHANTOM-9000"
    Then the search should return zero matching satellites
    And the system should respond with a structured error:
      """
      🚫 FLIGHT DIRECTOR — SATELLITE NOT FOUND
      No satellite matching "PHANTOM-9000" found in the CelesTrak catalog.
      Verify the satellite name or NORAD catalog number.
      Common targets: ISS, Hubble (HST), Starlink, GOES-16, Tiangong.
      """
    And the error_code should be "SATELLITE_NOT_FOUND"
    And the system should NOT fabricate orbital data
    And the system should NOT raise an unhandled exception

  @invalid-coordinates
  Scenario: Distorted geographic coordinates outside valid range
    Given the user provides coordinates latitude 999.0 and longitude -500.0
    When the input validation layer processes the request
    Then the coordinates should be rejected as invalid
    And the error message should explain:
      """
      🚫 FLIGHT DIRECTOR — INVALID COORDINATES
      Latitude must be between -90 and 90, longitude must be between
      -180 and 180. Received: (999.0, -500.0).
      """
    And the error_code should be "INVALID_COORDINATES"
    And no API calls should be made to CelesTrak or Open-Meteo

  @ambiguous-location
  Scenario: Ambiguous or unresolvable location name
    Given the user asks "ISS pass over Xyzzyville?"
    When the Weather & COMM Console geocoder attempts to resolve "Xyzzyville"
    Then the geocoder should return zero results
    And the system should respond:
      """
      🚫 FLIGHT DIRECTOR — LOCATION UNRESOLVED
      Could not resolve "Xyzzyville" to geographic coordinates.
      Provide a recognized city name or explicit latitude/longitude coordinates.
      """
    And the error_code should be "LOCATION_NOT_FOUND"

  @empty-input
  Scenario: Empty or nonsensical user query
    Given the user sends an empty message ""
    When the Flight Director attempts intent parsing
    Then the intent should be classified as "UNKNOWN"
    And the system should respond with usage guidance:
      """
      👋 SPACE OPERATIONS CO-PILOT — READY FOR TASKING
      Available mission operations:
        • "When does the ISS pass over New York?"
        • "Can I see Hubble from London tonight?"
        • "Show me Starlink passes over Tokyo this week"
        • "Where is the ISS right now?"
      """

  @hallucination-prevention @critical
  Scenario: System must not generate fabricated orbital data
    Given the user asks "What is the exact position of ISS right now?"
    When the GNC Console cannot reach CelesTrak due to network failure
    Then the system must NOT generate approximate or estimated positions
    And the system should respond with a data-unavailable notice:
      """
      ⚠️ GNC CONSOLE — DATA SOURCE UNAVAILABLE
      Unable to retrieve current TLE data from CelesTrak.
      Cannot provide orbital position data without verified source data.
      Please try again in a few moments.
      """
    And the response should set data_source to "UNAVAILABLE"
    And the response should NOT contain any latitude or longitude position values
    And the error_code should be "DATA_SOURCE_UNAVAILABLE"

  @invalid-time-window
  Scenario: Time window exceeds maximum allowed range
    Given the user asks "Show ISS passes for the next 30 days"
    When the Flight Director validates the time window
    Then the time window should be capped at 168 hours (7 days)
    And a notice should inform the user:
      """
      ℹ️ Time window capped to 7 days (168 hours) for TLE accuracy.
      Orbital predictions beyond 7 days from TLE epoch may have
      reduced accuracy due to atmospheric drag uncertainty.
      """
    And the pipeline should proceed with the capped window

  @concurrent-errors
  Scenario: Both CelesTrak and Open-Meteo APIs fail simultaneously
    Given the user asks "Can I see ISS from Bengaluru tonight?"
    When the GNC Console cannot reach CelesTrak
    And the Weather & COMM Console cannot reach Open-Meteo
    Then the GNC Console should return a DATA_SOURCE_UNAVAILABLE error
    And the Weather Console should apply fallback rule R-005
    And the Flight Director should aggregate errors into a combined notice:
      """
      ⚠️ FLIGHT DIRECTOR — MULTIPLE DATA SOURCES UNAVAILABLE
      • Orbital data: CelesTrak unreachable — cannot compute pass times
      • Weather data: Using fallback clear-sky assumption
      Unable to complete mission briefing. Please retry in a few moments.
      """
    And no fabricated data should appear in the response
