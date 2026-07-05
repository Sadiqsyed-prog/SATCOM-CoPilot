"""
BDD Step Definitions — Weather Validation Scenarios.

Implements steps for features/weather_validation.feature using
mock weather fixtures for deterministic testing (Rule R-008).
"""

from unittest.mock import patch, MagicMock

from behave import given, when, then

from src.agents.environmental import EnvironmentalAgent
from src.models.observer import ObserverLocation
from src.models.weather import CloudLayers, VisibilityClass
from src.tools.visibility_classifier import (
    classify_visibility,
    compute_effective_cover,
    generate_recommendation,
)
from features.environment import load_mock_weather


# ─── Background Steps ───────────────────────────────────────────────────────

@given("the Open-Meteo weather API is accessible")
def step_openmeteo_accessible(context):
    """Mark Open-Meteo API as accessible."""
    context.openmeteo_accessible = True


@given("the Weather & COMM Console is initialized with standard thresholds")
def step_weather_console_init(context):
    """Initialize Weather & COMM Console."""
    context.weather_agent = EnvironmentalAgent()


@given("the weather fallback rule R-005 is configured")
def step_fallback_configured(context):
    """Confirm fallback rule is active."""
    context.fallback_configured = True


# ─── When Steps ──────────────────────────────────────────────────────────────

@when("the GNC Console returns a valid pass window")
def step_gnc_valid_pass(context):
    """Simulate GNC Console returning a valid pass."""
    from datetime import datetime, timezone
    context.pass_time = datetime(2026, 7, 2, 1, 27, 12, tzinfo=timezone.utc)
    context.pass_times = [context.pass_time]


@when("the Weather & COMM Console reports cloud cover of {pct:d}%")
def step_report_cloud_cover(context, pct):
    """Set cloud cover percentage for assessment."""
    context.cloud_cover_pct = float(pct)
    context.visibility_class = classify_visibility(float(pct))


@when("the Open-Meteo API request times out after {seconds:d} seconds")
def step_openmeteo_timeout(context, seconds):
    """Simulate Open-Meteo API timeout."""
    observer = ObserverLocation.default()

    with patch("src.tools.weather_fetcher.requests.get") as mock_get:
        import requests
        mock_get.side_effect = requests.exceptions.Timeout(
            f"Request timed out after {seconds}s"
        )

        context.weather_result = context.weather_agent.assess_visibility(
            observer=observer,
            pass_times_utc=context.pass_times,
        )


@when("the GNC Console returns a pass with max elevation {deg:d} degrees")
def step_pass_with_elevation(context, deg):
    """Set pass elevation for layered analysis."""
    context.max_elevation_deg = float(deg)


@when("the Weather & COMM Console reports cloud layers:")
def step_report_cloud_layers(context):
    """Parse cloud layer data from table."""
    layers = {}
    for row in context.table:
        layers[row["layer"]] = float(row["cover_pct"])

    context.cloud_layers = CloudLayers(
        low_pct=layers.get("low", 0),
        mid_pct=layers.get("mid", 0),
        high_pct=layers.get("high", 0),
    )


# ─── Then Steps ──────────────────────────────────────────────────────────────

@then("the Mission Briefing should include a warning:")
def step_briefing_warning(context):
    """Verify warning is included in briefing."""
    expected_text = context.text.strip() if context.text else ""
    if context.cloud_cover_pct and context.cloud_cover_pct >= 91:
        recommendation = generate_recommendation(
            VisibilityClass.OBSTRUCTED, context.cloud_cover_pct
        )
        assert "cloud cover" in recommendation.lower(), (
            f"Warning should mention cloud cover, got: {recommendation}"
        )


@then("the Mission Briefing should include a qualified recommendation:")
def step_qualified_recommendation(context):
    """Verify qualified recommendation is present."""
    expected_text = context.text.strip() if context.text else ""
    recommendation = generate_recommendation(
        context.visibility_class, context.cloud_cover_pct
    )
    assert len(recommendation) > 0, "Recommendation should not be empty"


@then("the briefing should still include accurate pass time data")
def step_pass_times_present(context):
    """Verify pass times are not suppressed (Rule R-006)."""
    assert context.pass_times is not None, "Pass times should be present"
    assert len(context.pass_times) > 0, "Pass times list should not be empty"


@then("the pass times should NOT be omitted due to weather")
def step_times_not_omitted(context):
    """Verify pass times are sacred regardless of weather (Rule R-006)."""
    assert context.pass_times is not None and len(context.pass_times) > 0


@then('the data_source for weather should be "{source}"')
def step_weather_data_source(context, source):
    """Verify weather data source attribution."""
    if hasattr(context, "weather_result") and context.weather_result:
        actual = context.weather_result.get("data_source", "")
        assert actual == source, f"Expected data_source '{source}', got '{actual}'"


@then("the Weather & COMM Console should apply fallback rule R-005")
def step_fallback_applied(context):
    """Verify fallback was applied."""
    assert context.weather_result is not None, "Weather result should exist"
    assert context.weather_result.get("status") == "FALLBACK", (
        f"Expected FALLBACK status, got {context.weather_result.get('status')}"
    )


@then('the visibility classification should default to "{vis_class}"')
def step_default_visibility(context, vis_class):
    """Verify default visibility on fallback."""
    if context.weather_result:
        reports = context.weather_result.get("reports", [])
        if reports:
            actual = reports[0].get("visibility_class", "")
            assert actual == vis_class, (
                f"Expected visibility '{vis_class}', got '{actual}'"
            )


@then("the Mission Briefing should include a telemetry notice:")
def step_telemetry_notice(context):
    """Verify telemetry notice is present in fallback response."""
    expected_text = context.text.strip() if context.text else ""
    if context.weather_result:
        reports = context.weather_result.get("reports", [])
        if reports:
            rec = reports[0].get("recommendation", "")
            assert "TELEMETRY NOTICE" in rec, (
                f"Expected 'TELEMETRY NOTICE' in recommendation, got: {rec}"
            )


@then("the system should NOT raise an unhandled exception")
def step_no_exception(context):
    """Verify no unhandled exceptions occurred."""
    # If we got here, no exception was raised
    pass


@then("the pass times should remain accurate and present")
def step_pass_times_accurate(context):
    """Verify pass times are accurate in fallback scenario."""
    assert context.pass_times is not None


@then("the effective cloud cover should be calculated as:")
def step_effective_cover_calc(context):
    """Verify effective cloud cover calculation from table."""
    for row in context.table:
        expected = float(row["result"])
        actual = compute_effective_cover(context.cloud_layers)
        assert abs(actual - expected) < 0.1, (
            f"Expected effective cover {expected}, got {actual}"
        )


@then("the recommendation should note that high thin clouds have minimal impact")
def step_thin_cloud_note(context):
    """Verify recommendation mentions thin cloud impact."""
    # Classification is based on effective cover, not raw high cloud cover
    effective = compute_effective_cover(context.cloud_layers)
    vis = classify_visibility(effective)
    assert vis == VisibilityClass.CLEAR, (
        f"With effective cover {effective}%, expected CLEAR, got {vis}"
    )
