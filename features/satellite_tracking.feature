@satellite @tracking @core
Feature: Satellite Pass Tracking
  As a space enthusiast or ground station operator,
  I want to know when a specific satellite will pass over my location,
  So that I can plan observations or communication windows.

  Background:
    Given the CelesTrak TLE database is accessible
    And the GNC Console is initialized with SGP4 propagation
    And the default satellite is "ISS (ZARYA)" with NORAD ID 25544
    And the default observer location is Bengaluru at latitude 12.9716 and longitude 77.5946

  @happy-path @iss @clear-weather
  Scenario: ISS pass over Bengaluru with clear skies
    Given the user asks "When does the ISS pass over Bengaluru in the next 3 days?"
    When the Flight Director parses the intent
    Then the extracted intent should be "TRACK_PASS"
    And the extracted satellite should be "ISS (ZARYA)"
    And the extracted location should resolve to approximately:
      | field     | value  | tolerance |
      | latitude  | 12.97  | 0.5       |
      | longitude | 77.59  | 0.5       |

    When the GNC Console fetches TLE data for NORAD ID 25544
    Then the TLE data should contain exactly 2 lines
    And each TLE line should match the standard format checksum

    When the GNC Console computes visible passes for 72 hours
    Then at least 1 pass window should be returned
    And each pass window should contain:
      | field              | type     | constraint          |
      | rise_utc           | datetime | future              |
      | culmination_utc    | datetime | after rise_utc      |
      | set_utc            | datetime | after culmination   |
      | max_elevation_deg  | float    | between 0 and 90    |
      | duration_seconds   | integer  | between 60 and 600  |
      | is_sunlit          | boolean  | —                   |

    When the Weather & COMM Console checks weather for the first pass time
    And the cloud cover is less than 25%
    Then the visibility classification should be "CLEAR"
    And the final Mission Briefing should include a positive observation recommendation
    And the briefing should contain the satellite name, pass times, and weather summary
    And the data_source should be "CelesTrak"

  @multiple-passes
  Scenario: Multiple pass windows returned sorted chronologically
    Given the user asks "Show me all ISS passes over Tokyo this week"
    When the full pipeline executes successfully
    Then the passes should be sorted by "rise_utc" in ascending order
    And no two pass windows should overlap in time
    And each pass should have a unique rise_utc timestamp

  @high-elevation
  Scenario: Highlighting high-elevation passes for best visibility
    Given the user asks "Best ISS viewing opportunities over London?"
    When the full pipeline executes successfully
    Then passes with max_elevation_deg greater than 45 should be marked as "EXCELLENT"
    And passes with max_elevation_deg between 20 and 45 should be marked as "GOOD"
    And passes with max_elevation_deg less than 20 should be marked as "LOW"

  @default-satellite
  Scenario: Using default satellite when none specified
    Given the user asks "What passes over Bengaluru tonight?"
    When the Flight Director parses the intent
    Then the extracted satellite should default to "ISS (ZARYA)"
    And the NORAD ID should default to 25544

  @default-location
  Scenario: Using default location when none specified
    Given the user asks "When does the ISS pass overhead?"
    When the Flight Director parses the intent
    Then the extracted location should default to Bengaluru
    And the latitude should be approximately 12.9716
    And the longitude should be approximately 77.5946
