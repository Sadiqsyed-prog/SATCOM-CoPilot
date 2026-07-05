"""
Space Operations Co-Pilot — Flight Director (FD) Agent.

Central command authority for all mission operations. Parses natural
language user queries, dispatches to GNC and Weather & COMM consoles,
aggregates responses, and delivers formatted Mission Briefings.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from src.agents.environmental import EnvironmentalAgent
from src.agents.space_mechanics import SpaceMechanicsAgent
from src.config.guardrails import validate_coordinates, validate_time_window
from src.config.settings import (
    DEFAULT_NORAD_ID,
    DEFAULT_SATELLITE_NAME,
    DEFAULT_TIME_WINDOW_HOURS,
    SATELLITE_ALIASES,
    TIME_WINDOW_KEYWORDS,
)
from src.models.observer import ObserverLocation
from src.tools.geocoder import GeocodingError, geocode_city

logger = logging.getLogger(__name__)


class FlightDirector:
    """Flight Director (FD) Agent — Mission Command Authority.

    The primary entry point for all user interactions. Parses natural
    language intents, orchestrates sub-console agents, and aggregates
    results into Mission Briefing format.
    """

    def __init__(self) -> None:
        """Initialize Flight Director with sub-console agents."""
        self.gnc_console = SpaceMechanicsAgent()
        self.weather_console = EnvironmentalAgent()
        logger.info("Flight Director: Console initialized — GNC + Weather & COMM online")

    def parse_intent(self, query: str) -> dict:
        """Parse a natural language query to extract mission parameters.

        Args:
            query: User's natural language input.

        Returns:
            Dictionary with intent, satellite_name, norad_id, location,
            time_window_hours, and raw_query.
        """
        if not query or not query.strip():
            return {
                "intent": "UNKNOWN",
                "satellite_name": None,
                "norad_id": None,
                "location": None,
                "time_window_hours": DEFAULT_TIME_WINDOW_HOURS,
                "raw_query": query,
            }

        q_lower = query.lower().strip()

        # Classify intent
        intent = self._classify_intent(q_lower)

        # Extract satellite (primary — first match for non-fleet intents)
        sat_name, norad_id = self._extract_satellite(q_lower)

        # Extract ALL satellites for fleet/map intents
        all_satellites = self._extract_all_satellites(q_lower)

        # Extract location
        location = self._extract_location(query)

        # Extract time window
        time_window = self._extract_time_window(q_lower)

        return {
            "intent": intent,
            "satellite_name": sat_name,
            "norad_id": norad_id,
            "satellites_fleet": all_satellites,
            "location": location,
            "time_window_hours": time_window,
            "raw_query": query,
        }

    def execute_mission(self, query: str) -> dict:
        """Execute a complete mission from a user query.

        Full pipeline: parse → validate → dispatch → aggregate → report.

        Args:
            query: User's natural language input.

        Returns:
            Complete mission result dictionary.
        """
        logger.info("Flight Director: New mission — '%s'", query)

        # Step 1: Parse intent
        parsed = self.parse_intent(query)
        intent = parsed["intent"]

        # Step 2: Handle non-dispatch intents
        if intent == "UNKNOWN":
            return self._handle_unknown()

        if intent == "HELP":
            return self._handle_help()

        # Step 3: Resolve satellite
        sat_name = parsed["satellite_name"] or DEFAULT_SATELLITE_NAME
        norad_id = parsed["norad_id"] or DEFAULT_NORAD_ID

        # Step 4: Resolve observer location
        location_str = parsed["location"]
        try:
            if location_str:
                observer = geocode_city(location_str)
            else:
                observer = ObserverLocation.default()
        except GeocodingError as exc:
            return self._handle_error(
                "LOCATION_NOT_FOUND",
                f'Could not resolve location "{location_str}" to geographic '
                f"coordinates. Provide a recognized city name or explicit "
                f"latitude/longitude coordinates.",
            )

        # Step 5: Validate inputs
        is_valid, coord_err = validate_coordinates(
            observer.latitude, observer.longitude
        )
        if not is_valid:
            return self._handle_error("INVALID_COORDINATES", coord_err)

        time_window, time_notice = validate_time_window(
            parsed["time_window_hours"]
        )

        # Step 6: Dispatch to GNC Console
        tracking_result = None
        if intent in ("TRACK_PASS", "VISIBILITY_CHECK"):
            tracking_result = self.gnc_console.track_passes(
                satellite_name=sat_name,
                norad_id=norad_id,
                observer=observer,
                time_window_hours=time_window,
            )
        elif intent in ("SATELLITE_POSITION", "LIVE_TELEMETRY", "VISUALIZE_MAP"):
            tracking_result = self.gnc_console.get_position(
                satellite_name=sat_name,
                norad_id=norad_id,
                observer=observer,
            )

        # Check for tracking errors
        if tracking_result and tracking_result.get("status") == "ERROR":
            return tracking_result

        # Step 7: Dispatch to Weather & COMM Console
        weather_result = None
        if intent in ("TRACK_PASS", "VISIBILITY_CHECK") and tracking_result:
            passes = tracking_result.get("passes", [])
            if passes:
                pass_times = [
                    datetime.fromisoformat(str(p["culmination_utc"]))
                    for p in passes
                ]
                weather_result = self.weather_console.assess_visibility(
                    observer=observer,
                    pass_times_utc=pass_times,
                )

        # Step 8: Aggregate results
        result = {
            "status": "SUCCESS",
            "intent": intent,
            "satellite": sat_name,
            "norad_id": norad_id,
            "observer": observer.to_dict(),
            "data_source": tracking_result.get("data_source", "CelesTrak")
            if tracking_result else "CelesTrak",
        }

        if tracking_result:
            result["passes"] = tracking_result.get("passes", [])
            if "position" in tracking_result:
                result["position"] = tracking_result["position"]
            result["tle_epoch"] = tracking_result.get("tle_epoch")
            result["computation_engine"] = tracking_result.get(
                "computation_engine", "Skyfield/SGP4"
            )

        # Attach fleet list for VISUALIZE_MAP (used by the map tool)
        if intent == "VISUALIZE_MAP":
            result["satellites_fleet"] = parsed.get("satellites_fleet", [(sat_name, norad_id)])

        if weather_result:
            result["weather"] = weather_result

        if time_notice:
            result["notices"] = [time_notice]

        # Step 9: Generate Mission Briefing
        result["mission_briefing"] = self._format_mission_briefing(
            tracking_result, weather_result, sat_name, observer
        )

        logger.info("Flight Director: Mission complete for '%s'", query)
        return result

    def _classify_intent(self, q_lower: str) -> str:
        """Classify the user query into an intent category."""
        # VISUALIZE_MAP patterns (check before LIVE_TELEMETRY since 'see' is also a visibility word)
        map_words = ("map", "visualize", "plot", "show me on a map", "see on map", "show on map")
        if any(w in q_lower for w in map_words):
            return "VISUALIZE_MAP"

        # LIVE_TELEMETRY patterns
        telemetry_words = ("where is", "right now", "live telemetry", "currently", "live location")
        if any(w in q_lower for w in telemetry_words):
            return "LIVE_TELEMETRY"

        # SATELLITE_POSITION patterns
        position_words = ("position",)
        if any(w in q_lower for w in position_words):
            return "SATELLITE_POSITION"

        # VISIBILITY_CHECK patterns
        visibility_words = ("can i see", "visible", "visibility", "observe", "spot")
        if any(w in q_lower for w in visibility_words):
            return "VISIBILITY_CHECK"

        # TRACK_PASS patterns
        tracking_words = (
            "pass", "passes", "passing", "fly over", "flyover",
            "overhead", "when does", "when will", "show me", "track",
            "next pass", "what time",
        )
        if any(w in q_lower for w in tracking_words):
            return "TRACK_PASS"

        # HELP patterns
        help_words = ("help", "what can you", "how to", "usage", "capabilities")
        if any(w in q_lower for w in help_words):
            return "HELP"

        # Default: treat as TRACK_PASS if satellite name is found
        for alias in SATELLITE_ALIASES:
            if alias in q_lower:
                return "TRACK_PASS"

        return "UNKNOWN"

    def _extract_satellite(self, q_lower: str) -> tuple[str, int]:
        """Extract satellite name from query using alias matching."""
        # Check aliases (longest match first to avoid partial matches)
        sorted_aliases = sorted(SATELLITE_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in q_lower:
                name, norad_id = SATELLITE_ALIASES[alias]
                logger.info(
                    "Flight Director: Resolved satellite '%s' → %s (NORAD %d)",
                    alias, name, norad_id,
                )
                return name, norad_id

        # Default to ISS
        return DEFAULT_SATELLITE_NAME, DEFAULT_NORAD_ID

    def _extract_all_satellites(self, q_lower: str) -> list[tuple[str, int]]:
        """Extract ALL mentioned satellites from query (for fleet tracking).

        Returns a deduplicated list of (official_name, norad_id) tuples.
        If no satellites are found, returns the ISS default as a single-element list.
        """
        seen_norad_ids: set[int] = set()
        results: list[tuple[str, int]] = []

        sorted_aliases = sorted(SATELLITE_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in q_lower:
                name, norad_id = SATELLITE_ALIASES[alias]
                if norad_id not in seen_norad_ids:
                    seen_norad_ids.add(norad_id)
                    results.append((name, norad_id))
                    logger.info(
                        "Flight Director: Fleet — resolved '%s' → %s (NORAD %d)",
                        alias, name, norad_id,
                    )

        if not results:
            results.append((DEFAULT_SATELLITE_NAME, DEFAULT_NORAD_ID))

        return results

    def _extract_location(self, query: str) -> str | None:
        """Extract location name from query using word parsing."""
        import re
        # Find preposition
        match = re.search(r"(?i)\b(over|from|in|at|near)\s+(.*)", query)
        if not match:
            return None

        remainder = match.group(2)
        words = re.findall(r"[\w']+|[.,!?;]", remainder)
        
        stop_words = {"in", "for", "this", "next", "tonight", "tomorrow", "today", "and", "what", "is", "its", "condition", "pass", "through", "?", ".", "!", ","}
        
        location_words = []
        for word in words:
            if word.lower() in stop_words:
                break
            location_words.append(word)
            if len(location_words) >= 3:  # Max 3 words for a city name
                break
                
        location = " ".join(location_words).strip()
        if location and len(location) > 1:
            return location.title()

        return None

    def _extract_time_window(self, q_lower: str) -> int:
        """Extract time window from query using keyword matching."""
        # Check for explicit "next N days/hours"
        days_match = re.search(r"next\s+(\d+)\s+days?", q_lower)
        if days_match:
            return int(days_match.group(1)) * 24

        hours_match = re.search(r"next\s+(\d+)\s+hours?", q_lower)
        if hours_match:
            return int(hours_match.group(1))

        # Check keyword patterns
        for keyword, hours in TIME_WINDOW_KEYWORDS.items():
            if keyword in q_lower:
                return hours

        return DEFAULT_TIME_WINDOW_HOURS

    def _resolve_satellite(self, name: str) -> tuple[str, int]:
        """Map a satellite alias to its official name and NORAD ID."""
        key = name.lower().strip()
        if key in SATELLITE_ALIASES:
            return SATELLITE_ALIASES[key]
        return DEFAULT_SATELLITE_NAME, DEFAULT_NORAD_ID

    def _format_mission_briefing(
        self,
        tracking_result: dict | None,
        weather_result: dict | None,
        satellite_name: str,
        observer: ObserverLocation,
    ) -> str:
        """Format the ASCII Mission Briefing report."""
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║            SPACE OPERATIONS — MISSION BRIEFING              ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║ Target:   {satellite_name:<50}║",
            f"║ Observer: {observer.city or 'Unknown':<50}║",
            f"║          ({observer.latitude:.4f}°N, {observer.longitude:.4f}°E)"
            + " " * max(0, 36 - len(f"({observer.latitude:.4f}°N, {observer.longitude:.4f}°E)"))
            + "║",
            "╠══════════════════════════════════════════════════════════════╣",
        ]

        passes = (tracking_result or {}).get("passes", [])
        weather_reports = []
        if weather_result and isinstance(weather_result, dict):
            weather_reports = weather_result.get("reports", [])

        if not passes:
            lines.append("║ No passes found in the specified time window.              ║")
        else:
            for pw in passes:
                pn = pw.get("pass_number", "?")
                rise = str(pw.get("rise_utc", ""))[:19]
                culm = str(pw.get("culmination_utc", ""))[:19]
                sett = str(pw.get("set_utc", ""))[:19]
                elev = pw.get("max_elevation_deg", 0)
                sunlit = "YES" if pw.get("is_sunlit") else "NO"
                dur = pw.get("duration_seconds", 0)
                dur_m, dur_s = divmod(dur, 60)
                rating = pw.get("visibility_rating", "")

                lines.append(f"║ PASS #{pn} [{rating}]" + " " * max(0, 47 - len(f"PASS #{pn} [{rating}]")) + "║")
                lines.append(f"║   Rise:  {rise} UTC  (AZ: {pw.get('rise_azimuth_deg', 0):>5.1f}°)" + " " * 10 + "║")
                lines.append(f"║   Peak:  {culm} UTC  (EL: {elev:>5.1f}°)" + " " * 10 + "║")
                lines.append(f"║   Set:   {sett} UTC  (AZ: {pw.get('set_azimuth_deg', 0):>5.1f}°)" + " " * 10 + "║")
                lines.append(f"║   Duration: {dur_m}m {dur_s}s │ Sunlit: {sunlit}" + " " * 20 + "║")

                # Overlay weather if available
                for wr in weather_reports:
                    wr_time = str(wr.get("check_time_utc", ""))[:19]
                    if wr_time == culm:
                        vis = wr.get("visibility_class", "N/A")
                        cover = wr.get("cloud_cover_total_pct", 0)
                        lines.append(f"║   Weather: {vis} ({cover:.0f}% cloud)" + " " * 20 + "║")
                        break

                lines.append("║" + "─" * 62 + "║")

        # Sources
        sources = "CelesTrak · Skyfield/SGP4"
        if weather_result:
            w_src = weather_result.get("data_source", "Open-Meteo")
            sources += f" · {w_src}"
        lines.append(f"║ Sources: {sources:<52}║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")

        return "\n".join(lines)

    def _handle_error(self, error_code: str, message: str) -> dict:
        """Return a structured error response."""
        return {
            "status": "ERROR",
            "error_code": error_code,
            "error_message": message,
            "data_source": "UNAVAILABLE",
        }

    def _handle_unknown(self) -> dict:
        """Return usage guidance for unrecognized queries."""
        return {
            "status": "HELP",
            "intent": "UNKNOWN",
            "message": (
                "👋 SPACE OPERATIONS CO-PILOT — READY FOR TASKING\n"
                "Available mission operations:\n"
                '  • "When does the ISS pass over New York?"\n'
                '  • "Can I see Hubble from London tonight?"\n'
                '  • "Show me Starlink passes over Tokyo this week"\n'
                '  • "Where is the ISS right now?"'
            ),
        }

    def _handle_help(self) -> dict:
        """Return capabilities manifest."""
        return {
            "status": "HELP",
            "intent": "HELP",
            "message": (
                "🛰️ SPACE OPERATIONS CO-PILOT — CAPABILITIES\n\n"
                "I can help you with:\n"
                "  • Track satellite passes over any location\n"
                "  • Check weather conditions for observation\n"
                "  • Find the current position of satellites\n"
                "  • Assess visibility for upcoming passes\n\n"
                "Defaults:\n"
                "  • Satellite: ISS (ZARYA) — NORAD 25544\n"
                "  • Location: Bengaluru, India\n"
                "  • Time window: 72 hours (3 days)\n\n"
                "Supported satellites: ISS, Hubble (HST), Tiangong, "
                "GOES-16, Landsat 9"
            ),
        }
