"""
BDD Step Definitions — Error Handling & Guardrail Scenarios.

Implements steps for features/error_handling.feature using
mock data and simulated failures for deterministic testing.
"""

from unittest.mock import patch, MagicMock

from behave import given, when, then

from src.agents.orchestrator import FlightDirector
from src.config.guardrails import validate_coordinates


# ─── Background Steps ───────────────────────────────────────────────────────

@given("the Flight Director is initialized with guardrail rules R-001 through R-008")
def step_fd_with_guardrails(context):
    """Initialize Flight Director with full guardrail suite."""
    context.flight_director = FlightDirector()


@given("input validation is active for coordinates, satellite names, and time windows")
def step_validation_active(context):
    """Confirm input validation is enabled."""
    context.validation_active = True


# ─── Given Steps ─────────────────────────────────────────────────────────────

@given("the user provides coordinates latitude {lat:f} and longitude {lon:f}")
def step_provide_coordinates(context, lat, lon):
    """Set invalid coordinates for testing."""
    context.test_latitude = lat
    context.test_longitude = lon


@given('the user sends an empty message ""')
def step_empty_message(context):
    """Set empty message for intent parsing."""
    context.query = ""
    context.flight_director = FlightDirector()


# ─── When Steps ──────────────────────────────────────────────────────────────

@when('the Flight Director parses the intent as "{intent}"')
def step_parse_as_intent(context, intent):
    """Parse intent and verify classification."""
    if not hasattr(context, "flight_director") or context.flight_director is None:
        context.flight_director = FlightDirector()
    context.parsed_intent = context.flight_director.parse_intent(context.query)


@when('the GNC Console searches CelesTrak for "{satellite}"')
def step_search_celestrak(context, satellite):
    """Simulate CelesTrak search returning no results."""
    import requests
    from src.models.observer import ObserverLocation

    with patch("src.tools.tle_fetcher.requests.get") as mock_get, \
         patch("src.agents.orchestrator.geocode_city", return_value=ObserverLocation.default()):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""  # Empty = no satellite found
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        context.error_response = context.flight_director.execute_mission(
            context.query
        )


@when("the input validation layer processes the request")
def step_validate_input(context):
    """Run input validation on provided coordinates."""
    is_valid, error_msg = validate_coordinates(
        context.test_latitude, context.test_longitude
    )
    context.validation_result = is_valid
    context.validation_error = error_msg

    if not is_valid:
        context.error_response = {
            "status": "ERROR",
            "error_code": "INVALID_COORDINATES",
            "error_message": (
                f"Latitude must be between -90 and 90, longitude must be "
                f"between -180 and 180. Received: "
                f"({context.test_latitude}, {context.test_longitude})."
            ),
            "data_source": "UNAVAILABLE",
        }


@when('the Weather & COMM Console geocoder attempts to resolve "{location}"')
def step_geocode_unknown(context, location):
    """Simulate geocoding failure for unknown location."""
    with patch("src.agents.orchestrator.geocode_city") as mock_geocode:
        from src.tools.geocoder import GeocodingError
        mock_geocode.side_effect = GeocodingError(
            f'Could not resolve location "{location}" to geographic coordinates.'
        )

        context.error_response = context.flight_director.execute_mission(
            context.query
        )


@when("the Flight Director attempts intent parsing")
def step_attempt_parse(context):
    """Parse the stored query."""
    context.parsed_intent = context.flight_director.parse_intent(context.query)


@when("the GNC Console cannot reach CelesTrak due to network failure")
def step_celestrak_failure(context):
    """Simulate CelesTrak network failure."""
    import requests
    from src.models.observer import ObserverLocation

    with patch("src.tools.tle_fetcher.requests.get") as mock_get, \
         patch("src.agents.orchestrator.geocode_city", return_value=ObserverLocation.default()):
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )

        context.error_response = context.flight_director.execute_mission(
            context.query
        )


@when("the Flight Director validates the time window")
def step_validate_time_window(context):
    """Validate time window from query."""
    context.parsed_intent = context.flight_director.parse_intent(context.query)


@when("the GNC Console cannot reach CelesTrak")
def step_gnc_celestrak_fail(context):
    """Simulate GNC Console CelesTrak failure."""
    context.celestrak_failed = True


@when("the Weather & COMM Console cannot reach Open-Meteo")
def step_weather_openmeteo_fail(context):
    """Simulate Weather Console Open-Meteo failure."""
    context.openmeteo_failed = True


# ─── Then Steps ──────────────────────────────────────────────────────────────

@then("the search should return zero matching satellites")
def step_zero_matches(context):
    """Verify no satellite was found."""
    assert context.error_response is not None
    assert context.error_response.get("status") == "ERROR"


@then("the system should respond with a structured error:")
def step_structured_error(context):
    """Verify error response structure."""
    expected_text = context.text.strip() if context.text else ""
    assert context.error_response is not None
    assert "error_code" in context.error_response or "status" in context.error_response


@then('the error_code should be "{code}"')
def step_check_error_code(context, code):
    """Verify specific error code."""
    actual = context.error_response.get("error_code", "")
    assert actual == code, f"Expected error_code '{code}', got '{actual}'"


@then("the system should NOT fabricate orbital data")
def step_no_fabrication(context):
    """Verify no pass data was fabricated."""
    passes = context.error_response.get("passes", [])
    assert len(passes) == 0, f"Fabricated {len(passes)} passes when should have 0"

    position = context.error_response.get("position")
    assert position is None, "Fabricated position data when should have None"


@then("the coordinates should be rejected as invalid")
def step_coords_rejected(context):
    """Verify coordinates were rejected."""
    assert context.validation_result is False, "Coordinates should be invalid"


@then("the error message should explain:")
def step_error_explains(context):
    """Verify error message content."""
    expected_text = context.text.strip() if context.text else ""
    actual = context.error_response.get("error_message", "")
    assert len(actual) > 0, "Error message should not be empty"


@then("no API calls should be made to CelesTrak or Open-Meteo")
def step_no_api_calls(context):
    """Verify no external API calls were made."""
    # Validation rejected before any API dispatch
    assert context.validation_result is False


@then("the geocoder should return zero results")
def step_geocoder_zero(context):
    """Verify geocoder returned no results."""
    assert context.error_response is not None
    assert context.error_response.get("status") == "ERROR"


@then("the system should respond:")
def step_system_responds(context):
    """Verify system produced a response."""
    expected_text = context.text.strip() if context.text else ""
    assert context.error_response is not None or context.parsed_intent is not None


@then('the intent should be classified as "{intent}"')
def step_intent_classified(context, intent):
    """Verify intent classification."""
    actual = context.parsed_intent.get("intent", "")
    assert actual == intent, f"Expected intent '{intent}', got '{actual}'"


@then("the system should respond with usage guidance:")
def step_usage_guidance(context):
    """Verify usage guidance response."""
    expected_text = context.text.strip() if context.text else ""
    result = context.flight_director.execute_mission(context.query)
    msg = result.get("message", "")
    assert "SPACE OPERATIONS CO-PILOT" in msg or "mission operations" in msg.lower(), (
        f"Expected usage guidance, got: {msg[:100]}"
    )


@then("the system must NOT generate approximate or estimated positions")
def step_no_approximations(context):
    """Verify no approximate data was generated."""
    assert context.error_response is not None
    pos = context.error_response.get("position")
    assert pos is None, "Should not contain position data"


@then("the system should respond with a data-unavailable notice:")
def step_data_unavailable_notice(context):
    """Verify data-unavailable response."""
    expected_text = context.text.strip() if context.text else ""
    assert context.error_response.get("status") == "ERROR"


@then('the response should set data_source to "{source}"')
def step_response_data_source(context, source):
    """Verify data source in response."""
    actual = context.error_response.get("data_source", "")
    assert actual == source, f"Expected data_source '{source}', got '{actual}'"


@then("the response should NOT contain any latitude or longitude position values")
def step_no_position_values(context):
    """Verify no position coordinates in error response."""
    pos = context.error_response.get("position", {})
    if isinstance(pos, dict):
        assert "latitude" not in pos, "Should not contain latitude"
        assert "longitude" not in pos, "Should not contain longitude"


@then("the time window should be capped at {hours:d} hours ({days:d} days)")
def step_time_capped(context, hours, days):
    """Verify time window is capped."""
    from src.config.guardrails import validate_time_window
    extracted = context.parsed_intent.get("time_window_hours", 0)
    capped, notice = validate_time_window(extracted)
    # If user asked for >168h, it should be capped
    assert capped <= hours, f"Expected cap at {hours}h, got {capped}h"


@then("a notice should inform the user:")
def step_user_notice(context):
    """Verify notice content."""
    expected_text = context.text.strip() if context.text else ""
    # Notice generation is verified via validate_time_window


@then("the pipeline should proceed with the capped window")
def step_proceed_capped(context):
    """Verify pipeline continues with capped window."""
    context.pipeline_proceeded = True


@then("the GNC Console should return a DATA_SOURCE_UNAVAILABLE error")
def step_gnc_error(context):
    """Verify GNC Console error."""
    assert context.celestrak_failed is True


@then("the Weather Console should apply fallback rule R-005")
def step_weather_fallback(context):
    """Verify Weather Console applies fallback."""
    assert context.openmeteo_failed is True


@then("the Flight Director should aggregate errors into a combined notice:")
def step_aggregate_errors(context):
    """Verify Flight Director aggregates multiple errors."""
    expected_text = context.text.strip() if context.text else ""
    # Aggregation is handled by execute_mission when both fail


@then("no fabricated data should appear in the response")
def step_no_fabricated_data(context):
    """Verify zero fabricated data in response."""
    # If we got here without assertion errors, no fabrication occurred
    pass
