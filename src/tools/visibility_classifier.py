"""
Space Operations Co-Pilot — Visibility Classifier.

Classifies satellite observation feasibility based on cloud cover
percentages, atmospheric layers, and pass elevation angles.
"""

from __future__ import annotations

from src.config.settings import CLOUD_LAYER_FACTORS, VISIBILITY_THRESHOLDS
from src.models.weather import CloudLayers, VisibilityClass


def classify_visibility(cloud_cover_pct: float) -> VisibilityClass:
    """Map cloud cover percentage to a VisibilityClass.

    Args:
        cloud_cover_pct: Total or effective cloud cover (0–100).

    Returns:
        VisibilityClass enum member.
    """
    pct = max(0.0, min(100.0, cloud_cover_pct))

    for class_name, (low, high) in VISIBILITY_THRESHOLDS.items():
        if low <= pct <= high:
            return VisibilityClass(class_name)

    # Fallback: ≥91% is OBSTRUCTED
    return VisibilityClass.OBSTRUCTED


def compute_effective_cover(cloud_layers: CloudLayers) -> float:
    """Compute effective cloud cover using layer impact factors.

    Different cloud layers have varying impact on satellite visibility:
    - Low clouds (stratus, <2km): full blockage (×1.0)
    - Mid clouds (alto, 2-6km): moderate blockage (×0.8)
    - High clouds (cirrus, >6km): minimal blockage (×0.4)

    Formula: max(low×1.0, mid×0.8, high×0.4)

    Args:
        cloud_layers: CloudLayers object with per-layer percentages.

    Returns:
        Effective cloud cover percentage (0–100).
    """
    return max(
        cloud_layers.low_pct * CLOUD_LAYER_FACTORS["low"],
        cloud_layers.mid_pct * CLOUD_LAYER_FACTORS["mid"],
        cloud_layers.high_pct * CLOUD_LAYER_FACTORS["high"],
    )


def adjust_for_elevation(
    effective_cover: float,
    max_elevation_deg: float,
) -> float:
    """Adjust effective cloud cover based on pass elevation.

    Higher-elevation passes are more forgiving of partial cloud cover
    because the atmospheric path is shorter at higher angles.

    Args:
        effective_cover: Base effective cloud cover (0–100).
        max_elevation_deg: Maximum pass elevation in degrees (0–90).

    Returns:
        Adjusted cloud cover percentage.
    """
    elevation_factor = 1.0 - (max_elevation_deg / 90.0) * 0.3
    return effective_cover * elevation_factor


def generate_recommendation(
    visibility_class: VisibilityClass,
    cloud_cover_pct: float,
) -> str:
    """Generate a human-readable observation recommendation.

    Args:
        visibility_class: Classified visibility level.
        cloud_cover_pct: Cloud cover percentage for display.

    Returns:
        Emoji-prefixed recommendation string.
    """
    cover = int(cloud_cover_pct)

    templates = {
        VisibilityClass.CLEAR: (
            f"☀️ Excellent viewing conditions expected. "
            f"Clear skies with {cover}% cloud cover. "
            f"Recommended for visual satellite observation."
        ),
        VisibilityClass.MOSTLY_CLEAR: (
            f"🌤️ Good viewing conditions with {cover}% cloud cover. "
            f"Satellite should be visible during clear intervals."
        ),
        VisibilityClass.PARTIAL: (
            f"⛅ Partial cloud cover ({cover}%) may intermittently "
            f"obscure the satellite. Observation is possible but not "
            f"guaranteed. Best viewing during breaks in cloud cover "
            f"near the culmination point."
        ),
        VisibilityClass.MOSTLY_CLOUDY: (
            f"🌥️ Significant cloud cover ({cover}%) expected during "
            f"this pass. Visual observation is unlikely but not "
            f"impossible. Consider monitoring conditions closer to "
            f"pass time for potential clearing."
        ),
        VisibilityClass.OBSTRUCTED: (
            f"☁️ Heavy cloud cover ({cover}%) is expected during this "
            f"pass. Visual observation is very unlikely. Consider "
            f"monitoring the next available pass window or using "
            f"radio tracking instead."
        ),
    }

    return templates.get(visibility_class, f"Cloud cover: {cover}%")


def get_observation_likelihood(visibility_class: VisibilityClass) -> str:
    """Map VisibilityClass to a human-readable likelihood label.

    Args:
        visibility_class: Classified visibility level.

    Returns:
        Likelihood string.
    """
    mapping = {
        VisibilityClass.CLEAR: "Excellent",
        VisibilityClass.MOSTLY_CLEAR: "Good",
        VisibilityClass.PARTIAL: "Possible",
        VisibilityClass.MOSTLY_CLOUDY: "Unlikely",
        VisibilityClass.OBSTRUCTED: "Very Unlikely",
    }
    return mapping.get(visibility_class, "Unknown")
