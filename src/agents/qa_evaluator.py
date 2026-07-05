"""
Space Operations Co-Pilot — QA / Evaluation Agent.

Independent verification layer that validates pipeline outputs
for schema compliance, hallucination indicators, guardrail
adherence, and logical consistency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config.guardrails import validate_azimuth, validate_cloud_cover, validate_elevation

logger = logging.getLogger(__name__)


class QAEvaluator:
    """QA / Evaluation Agent.

    Runs automated quality assurance checks on every pipeline output.
    Detects hallucinations, validates schemas, and ensures guardrail compliance.
    """

    def validate_response(self, response: dict) -> dict:
        """Run all validation checks on a pipeline response.

        Args:
            response: The pipeline output dictionary to validate.

        Returns:
            Validation result with pass/fail status and issue details.
        """
        issues: list[str] = []

        issues.extend(self._validate_schema(response))
        issues.extend(self._detect_hallucinations(response))
        issues.extend(self._check_guardrails(response))
        issues.extend(self._cross_validate(response))

        is_pass = len(issues) == 0

        result = {
            "status": "PASS" if is_pass else "FAIL",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_checks": 4,
            "issues_found": len(issues),
            "issues": issues,
            "categories": {
                "schema": [i for i in issues if i.startswith("[SCHEMA]")],
                "hallucination": [i for i in issues if i.startswith("[HALLUCINATION]")],
                "guardrail": [i for i in issues if i.startswith("[GUARDRAIL]")],
                "consistency": [i for i in issues if i.startswith("[CONSISTENCY]")],
            },
        }

        if is_pass:
            logger.info("QA Agent: All validation checks PASSED")
        else:
            logger.warning("QA Agent: %d issue(s) found", len(issues))
            for issue in issues:
                logger.warning("  → %s", issue)

        return result

    def _validate_schema(self, response: dict) -> list[str]:
        """Check required fields exist and have valid types/ranges."""
        issues = []

        # Status field is always required
        if "status" not in response:
            issues.append("[SCHEMA] Missing required field: 'status'")
            return issues

        status = response["status"]

        if status == "SUCCESS":
            # Success responses must have data fields
            for field in ("satellite", "norad_id", "data_source"):
                if field not in response:
                    issues.append(f"[SCHEMA] Missing required field: '{field}'")

            # Validate pass windows if present
            for i, pw in enumerate(response.get("passes", [])):
                for field in ("rise_utc", "culmination_utc", "set_utc",
                              "max_elevation_deg", "duration_seconds"):
                    if field not in pw:
                        issues.append(
                            f"[SCHEMA] Pass #{i+1} missing field: '{field}'"
                        )

                if "max_elevation_deg" in pw:
                    if not validate_elevation(pw["max_elevation_deg"]):
                        issues.append(
                            f"[SCHEMA] Pass #{i+1} max_elevation_deg "
                            f"out of range [0, 90]: {pw['max_elevation_deg']}"
                        )

                for az_field in ("rise_azimuth_deg", "set_azimuth_deg"):
                    if az_field in pw and not validate_azimuth(pw[az_field]):
                        issues.append(
                            f"[SCHEMA] Pass #{i+1} {az_field} "
                            f"out of range [0, 360]: {pw[az_field]}"
                        )

        elif status == "ERROR":
            for field in ("error_code", "error_message"):
                if field not in response:
                    issues.append(f"[SCHEMA] Error response missing: '{field}'")

        return issues

    def _detect_hallucinations(self, response: dict) -> list[str]:
        """Check for fabricated data without verified sources."""
        issues = []

        data_source = response.get("data_source", "")

        # R-001: No orbital data without verified TLE source
        if data_source == "UNAVAILABLE":
            if response.get("passes"):
                issues.append(
                    "[HALLUCINATION] CRITICAL: Pass data present with "
                    "data_source='UNAVAILABLE' — fabricated orbital data detected"
                )
            if response.get("position"):
                issues.append(
                    "[HALLUCINATION] CRITICAL: Position data present with "
                    "data_source='UNAVAILABLE' — fabricated position detected"
                )

        # Check pass time plausibility (ISS period ≈ 92.68 min)
        passes = response.get("passes", [])
        for i in range(1, len(passes)):
            try:
                prev_rise = datetime.fromisoformat(
                    str(passes[i - 1].get("rise_utc", ""))
                )
                curr_rise = datetime.fromisoformat(
                    str(passes[i].get("rise_utc", ""))
                )
                gap_minutes = (curr_rise - prev_rise).total_seconds() / 60
                if gap_minutes < 80:
                    issues.append(
                        f"[HALLUCINATION] Passes #{i} and #{i+1} are only "
                        f"{gap_minutes:.0f} min apart (ISS period ≈ 93 min)"
                    )
            except (ValueError, TypeError):
                continue

        return issues

    def _check_guardrails(self, response: dict) -> list[str]:
        """Verify behavioral rule compliance."""
        issues = []

        # R-004: Data source attribution required
        if "data_source" not in response:
            issues.append(
                "[GUARDRAIL] Missing 'data_source' field (Rule R-004)"
            )

        # Check for raw tracebacks in user-facing text
        for field in ("error_message", "recommendation"):
            value = str(response.get(field, ""))
            if "Traceback" in value or "File \"" in value:
                issues.append(
                    f"[GUARDRAIL] Raw traceback detected in '{field}' — "
                    f"must not expose internal errors to user"
                )

        # R-006: Pass times must not be suppressed by weather
        weather = response.get("weather", {})
        if isinstance(weather, dict):
            vis_class = weather.get("visibility_class", "")
            if vis_class in ("OBSTRUCTED", "MOSTLY_CLOUDY"):
                if not response.get("passes"):
                    issues.append(
                        "[GUARDRAIL] Pass data missing when weather is "
                        f"'{vis_class}' — Rule R-006 violation"
                    )

        return issues

    def _cross_validate(self, response: dict) -> list[str]:
        """Check logical consistency of response data."""
        issues = []

        for i, pw in enumerate(response.get("passes", [])):
            try:
                rise = datetime.fromisoformat(str(pw.get("rise_utc", "")))
                culm = datetime.fromisoformat(str(pw.get("culmination_utc", "")))
                sett = datetime.fromisoformat(str(pw.get("set_utc", "")))

                if not (rise < culm < sett):
                    issues.append(
                        f"[CONSISTENCY] Pass #{i+1}: Times not in order "
                        f"(rise < culmination < set)"
                    )

                duration = pw.get("duration_seconds", 0)
                actual = int((sett - rise).total_seconds())
                if abs(duration - actual) > 2:
                    issues.append(
                        f"[CONSISTENCY] Pass #{i+1}: duration_seconds={duration} "
                        f"doesn't match rise→set delta={actual}s"
                    )

            except (ValueError, TypeError):
                issues.append(
                    f"[CONSISTENCY] Pass #{i+1}: Invalid datetime format"
                )

        return issues
