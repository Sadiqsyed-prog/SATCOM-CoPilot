@weather @visibility
Feature: Weather-Gated Visibility Assessment
  As a satellite observer,
  I want to know if weather conditions will permit visual observation,
  So that I don't waste time preparing for an invisible pass.

  Background:
    Given the Open-Meteo weather API is accessible
    And the Weather & COMM Console is initialized with standard thresholds
    And the weather fallback rule R-005 is configured

  @overcast @blocked
  Scenario: Satellite pass completely blocked by cloud cover
    Given the user asks "Can I see the ISS tonight from Mumbai?"
    When the GNC Console returns a valid pass window
    And the Weather & COMM Console reports cloud cover of 95%
    Then the visibility classification should be "OBSTRUCTED"
    And the Mission Briefing should include a warning:
      """
      ☁️ Heavy cloud cover (95%) is expected during this pass.
      Visual observation is very unlikely. Consider monitoring the next
      available pass window or using radio tracking instead.
      """
    And the briefing should still include accurate pass time data
    And the pass times should NOT be omitted due to weather
    And the data_source for weather should be "Open-Meteo"

  @partial-clouds
  Scenario: Partially cloudy conditions with qualified recommendation
    Given the user asks "ISS pass visibility over Delhi tomorrow?"
    When the GNC Console returns a valid pass window
    And the Weather & COMM Console reports cloud cover of 55%
    Then the visibility classification should be "PARTIAL"
    And the Mission Briefing should include a qualified recommendation:
      """
      ⛅ Partial cloud cover (55%) may intermittently obscure the satellite.
      Observation is possible but not guaranteed. Best viewing during
      breaks in cloud cover near the culmination point.
      """

  @api-degraded @fallback
  Scenario: Weather API timeout with graceful fallback to clear sky
    Given the user asks "ISS pass over Sydney?"
    When the GNC Console returns a valid pass window
    But the Open-Meteo API request times out after 10 seconds
    Then the Weather & COMM Console should apply fallback rule R-005
    And the visibility classification should default to "CLEAR"
    And the data_source for weather should be "FALLBACK_CLEAR_SKY"
    And the Mission Briefing should include a telemetry notice:
      """
      ℹ️ TELEMETRY NOTICE: Weather data temporarily unavailable.
      Assuming clear-sky conditions. Verify local weather independently
      before planning your observation session.
      """
    And the system should NOT raise an unhandled exception
    And the pass times should remain accurate and present

  @layered-clouds
  Scenario: Layered cloud analysis for precise visibility assessment
    Given the user asks "Can I observe ISS from Bengaluru tonight?"
    When the GNC Console returns a pass with max elevation 65 degrees
    And the Weather & COMM Console reports cloud layers:
      | layer | cover_pct |
      | low   | 10        |
      | mid   | 25        |
      | high  | 60        |
    Then the effective cloud cover should be calculated as:
      | computation                          | result |
      | max(10*1.0, 25*0.8, 60*0.4)         | 24.0   |
    And the visibility classification should be "CLEAR"
    And the recommendation should note that high thin clouds have minimal impact
