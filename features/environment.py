"""
Behave environment hooks for Space Operations Co-Pilot BDD tests.

Sets up mock data, initializes agents with fixtures, and provides
helper functions for loading test data.
"""

import json
import os
import sys

# Ensure project root is on Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FIXTURES_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures")


def before_all(context):
    """Run once before all tests — set up shared state."""
    context.fixtures_dir = FIXTURES_DIR
    context.project_root = PROJECT_ROOT


def before_scenario(context, scenario):
    """Run before each scenario — reset state and load fixtures."""
    context.query = None
    context.parsed_intent = None
    context.tracking_result = None
    context.weather_result = None
    context.error_response = None
    context.flight_director = None
    context.mock_tle_data = None
    context.mock_weather_data = None


def after_scenario(context, scenario):
    """Run after each scenario — cleanup."""
    pass


def load_mock_tle(fixture_name: str) -> str:
    """Load a mock TLE fixture file.

    Args:
        fixture_name: Filename in tests/fixtures/ (e.g., 'tle_iss_mock.txt').

    Returns:
        Raw TLE text content.
    """
    path = os.path.join(FIXTURES_DIR, fixture_name)
    with open(path, "r") as f:
        return f.read()


def load_mock_weather(fixture_name: str) -> dict:
    """Load a mock weather fixture file.

    Args:
        fixture_name: Filename in tests/fixtures/ (e.g., 'weather_clear_mock.json').

    Returns:
        Parsed JSON dictionary.
    """
    path = os.path.join(FIXTURES_DIR, fixture_name)
    with open(path, "r") as f:
        return json.load(f)
