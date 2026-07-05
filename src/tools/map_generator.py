"""
Space Operations Co-Pilot — Interactive Map Generator.

Generates interactive Folium maps plotting real-time satellite
positions using SGP4 telemetry data. Supports both single-shot
static maps, single-satellite live tracking, and multi-satellite
fleet tracking dashboards with auto-refresh.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
import webbrowser
from pathlib import Path

import folium

logger = logging.getLogger(__name__)

# Persistent output directory for map files
MAP_DIR = os.path.join(tempfile.gettempdir(), "satcom_copilot")
LIVE_MAP_FILENAME = "live_map.html"
STATIC_MAP_FILENAME = "satellite_map.html"

# Color palette for fleet tracking (cycled if more than 8 satellites)
FLEET_COLORS = [
    ("orange", "fa-satellite", "\U0001f7e0"),
    ("blue", "fa-satellite", "\U0001f535"),
    ("purple", "fa-satellite", "\U0001f7e3"),
    ("red", "fa-satellite", "\U0001f534"),
    ("green", "fa-satellite", "\U0001f7e2"),
    ("darkblue", "fa-satellite", "\U00002b1c"),
    ("cadetblue", "fa-satellite", "\U0001f7e4"),
    ("pink", "fa-satellite", "\U0001f7e1"),
]


def _build_satellite_map(
    satellites: list[dict],
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_city: str | None = None,
    auto_refresh_seconds: int | None = None,
) -> folium.Map:
    """Build a Folium Map object with one or more satellite markers.

    This is the internal map construction engine used by both
    single-shot and live-tracking modes. It handles any number
    of satellites on a single map.

    Args:
        satellites: List of position dicts, each containing at minimum:
            name, latitude, longitude, altitude_km, speed_kmh,
            is_sunlit, compass_direction, sky_position, timestamp_utc.
        observer_lat: Observer's latitude (optional).
        observer_lon: Observer's longitude (optional).
        observer_city: Observer's city name (optional).
        auto_refresh_seconds: If set, injects a <meta> auto-refresh tag.

    Returns:
        Configured folium.Map object ready to be saved.
    """
    # -- Determine center and zoom from satellite positions --
    lats = [s.get("latitude", 0) for s in satellites]
    lons = [s.get("longitude", 0) for s in satellites]

    if observer_lat is not None:
        lats.append(observer_lat)
    if observer_lon is not None:
        lons.append(observer_lon)

    center_lat = sum(lats) / len(lats) if lats else 0
    center_lon = sum(lons) / len(lons) if lons else 0

    sat_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=3,
        tiles="CartoDB dark_matter",
        attr="CartoDB",
    )

    # -- Inject auto-refresh meta tag for live tracking --
    if auto_refresh_seconds is not None:
        sat_map.get_root().header.add_child(
            folium.Element(
                f"<meta http-equiv='refresh' content='{auto_refresh_seconds}'>"
            )
        )

    # -- Plot each satellite --
    for idx, sat in enumerate(satellites):
        color_info = FLEET_COLORS[idx % len(FLEET_COLORS)]
        marker_color = color_info[0]

        name = sat.get("name", f"Satellite {idx + 1}")
        latitude = sat.get("latitude", 0)
        longitude = sat.get("longitude", 0)
        altitude_km = sat.get("altitude_km", 0)
        speed_kmh = sat.get("speed_kmh", 0)
        is_sunlit = sat.get("is_sunlit", False)
        compass_direction = sat.get("compass_direction", "")
        sky_position = sat.get("sky_position", "")
        timestamp_utc = sat.get("timestamp_utc", "")

        sunlit_icon = "sun" if is_sunlit else "moon"
        sunlit_text = "\U0001f31e Sunlit" if is_sunlit else "\U0001f311 In Shadow"

        # -- Satellite popup --
        sat_popup_html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 260px;">
            <h3 style="margin:0 0 8px 0; color: #00d4ff;">\U0001f6f0\ufe0f {name}</h3>
            <table style="font-size: 13px; border-collapse: collapse; width: 100%;">
                <tr><td style="padding:3px 8px; color:#888;">Timestamp</td>
                    <td style="padding:3px 8px; font-weight:600;">{timestamp_utc[:19]} UTC</td></tr>
                <tr style="background:#1a1a2e;"><td style="padding:3px 8px; color:#888;">Latitude</td>
                    <td style="padding:3px 8px; font-weight:600;">{latitude:.4f}\u00b0</td></tr>
                <tr><td style="padding:3px 8px; color:#888;">Longitude</td>
                    <td style="padding:3px 8px; font-weight:600;">{longitude:.4f}\u00b0</td></tr>
                <tr style="background:#1a1a2e;"><td style="padding:3px 8px; color:#888;">Altitude</td>
                    <td style="padding:3px 8px; font-weight:600;">{altitude_km:.1f} km</td></tr>
                <tr><td style="padding:3px 8px; color:#888;">Speed</td>
                    <td style="padding:3px 8px; font-weight:600;">{speed_kmh:,.1f} km/h</td></tr>
                <tr style="background:#1a1a2e;"><td style="padding:3px 8px; color:#888;">Illumination</td>
                    <td style="padding:3px 8px; font-weight:600;">{sunlit_text}</td></tr>
            </table>
        </div>
        """

        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(sat_popup_html, max_width=320),
            tooltip=f"{name} \u2014 {altitude_km:.0f} km",
            icon=folium.Icon(
                color=marker_color,
                icon=sunlit_icon,
                prefix="fa",
            ),
        ).add_to(sat_map)

        # -- Ground footprint --
        folium.Circle(
            location=[latitude, longitude],
            radius=altitude_km * 1000 * 2.0,
            color="#00d4ff",
            fill=True,
            fill_color="#00d4ff",
            fill_opacity=0.06,
            weight=1,
        ).add_to(sat_map)

        # -- Line of sight from observer to each satellite --
        if observer_lat is not None and observer_lon is not None:
            folium.PolyLine(
                locations=[
                    [observer_lat, observer_lon],
                    [latitude, longitude],
                ],
                color="#ffcc00",
                weight=2,
                dash_array="8",
                opacity=0.5,
            ).add_to(sat_map)

    # -- Observer marker --
    if observer_lat is not None and observer_lon is not None:
        obs_label = observer_city or "Observer"
        obs_popup_html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h4 style="margin:0 0 6px 0; color: #4eff4e;">\U0001f4cd {obs_label}</h4>
            <p style="font-size:13px; margin:2px 0;">Lat: {observer_lat:.4f}\u00b0, Lon: {observer_lon:.4f}\u00b0</p>
            <p style="font-size:13px; margin:2px 0;">Tracking {len(satellites)} satellite(s)</p>
        </div>
        """
        folium.Marker(
            location=[observer_lat, observer_lon],
            popup=folium.Popup(obs_popup_html, max_width=280),
            tooltip=f"{obs_label} (Observer)",
            icon=folium.Icon(color="green", icon="user", prefix="fa"),
        ).add_to(sat_map)

    # -- Auto-fit bounds to show all markers --
    if len(lats) >= 2:
        sw = [min(lats) - 5, min(lons) - 5]
        ne = [max(lats) + 5, max(lons) + 5]
        sat_map.fit_bounds([sw, ne])

    # -- Mode label and title HUD --
    is_fleet = len(satellites) > 1
    mode_label = "FLEET TRACKING" if is_fleet else "LIVE TRACKING"
    if auto_refresh_seconds is None:
        mode_label = "Position Snapshot"

    sat_names_str = " | ".join(s.get("name", "?") for s in satellites)
    first = satellites[0] if satellites else {}

    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                z-index: 9999; background: rgba(10,10,30,0.85); color: #00d4ff;
                padding: 12px 24px; border-radius: 8px; font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px; font-weight: 600; border: 1px solid #00d4ff40;
                backdrop-filter: blur(8px); text-align: center; max-width: 90%;">
        \U0001f6f0\ufe0f {mode_label} \u2014 {sat_names_str}
        <div style="font-size: 11px; color: #aaa; margin-top: 4px;">
            {first.get('timestamp_utc', '')[:19]} UTC &nbsp;|&nbsp;
            {len(satellites)} satellite(s) tracked
        </div>
    </div>
    """
    sat_map.get_root().html.add_child(folium.Element(title_html))

    return sat_map


def generate_satellite_map(
    satellite_name: str,
    latitude: float,
    longitude: float,
    altitude_km: float = 0.0,
    speed_kmh: float = 0.0,
    is_sunlit: bool = False,
    compass_direction: str = "",
    sky_position: str = "",
    timestamp_utc: str = "",
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_city: str | None = None,
    open_browser: bool = True,
) -> str:
    """Generate a single-shot interactive Folium map (no auto-refresh).

    Convenience wrapper for single-satellite snapshots.

    Returns:
        Absolute path to the saved HTML map file.
    """
    logger.info(
        "Map Generator: Static snapshot — %s at (%.4f, %.4f)",
        satellite_name, latitude, longitude,
    )

    sat_entry = {
        "name": satellite_name,
        "latitude": latitude,
        "longitude": longitude,
        "altitude_km": altitude_km,
        "speed_kmh": speed_kmh,
        "is_sunlit": is_sunlit,
        "compass_direction": compass_direction,
        "sky_position": sky_position,
        "timestamp_utc": timestamp_utc,
    }

    sat_map = _build_satellite_map(
        satellites=[sat_entry],
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_city=observer_city,
        auto_refresh_seconds=None,
    )

    os.makedirs(MAP_DIR, exist_ok=True)
    map_path = os.path.join(MAP_DIR, STATIC_MAP_FILENAME)
    sat_map.save(map_path)
    logger.info("Map Generator: Saved static map to %s", map_path)

    if open_browser:
        webbrowser.open(f"file:///{Path(map_path).as_posix()}")

    return map_path


def start_live_tracking(
    satellites: list[tuple[str, int]],
    observer_lat: float,
    observer_lon: float,
    observer_elevation_m: float = 0.0,
    observer_city: str = "",
    refresh_seconds: int = 3,
) -> None:
    """Start a live-updating satellite tracking dashboard.

    Supports tracking a single satellite or a fleet of multiple
    satellites on the same map. TLE data is fetched once per satellite
    at startup. The SGP4 position is recomputed every cycle.

    Args:
        satellites: List of (satellite_name, norad_id) tuples.
            Pass a single-element list for single tracking.
        observer_lat: Observer latitude in degrees.
        observer_lon: Observer longitude in degrees.
        observer_elevation_m: Observer elevation in meters.
        observer_city: Observer city name for display.
        refresh_seconds: Seconds between position updates (default 3).

    Raises:
        RuntimeError: If TLE data cannot be fetched for any satellite.
    """
    # Lazy imports to avoid circular dependencies at module level
    from src.models.observer import ObserverLocation
    from src.tools.pass_calculator import get_satellite_position
    from src.tools.tle_fetcher import TLEFetchError, fetch_tle_by_norad_id

    logger.info(
        "Map Generator: Starting live tracking for %d satellite(s): %s",
        len(satellites),
        ", ".join(f"{n} ({nid})" for n, nid in satellites),
    )

    # Step 1: Fetch TLE data once for each satellite
    tle_cache = {}  # norad_id → (name, tle_data)
    for sat_name, norad_id in satellites:
        try:
            tle_data = fetch_tle_by_norad_id(norad_id)
            tle_cache[norad_id] = (sat_name, tle_data)
            logger.info("Map Generator: TLE acquired for %s (NORAD %d)", sat_name, norad_id)
        except TLEFetchError as exc:
            raise RuntimeError(
                f"TLE fetch failed for {sat_name} (NORAD {norad_id}): {exc}"
            ) from exc

    # Build observer
    observer = ObserverLocation(
        city=observer_city or None,
        latitude=observer_lat,
        longitude=observer_lon,
        elevation_m=observer_elevation_m,
    )

    # Prepare output path
    os.makedirs(MAP_DIR, exist_ok=True)
    map_path = os.path.join(MAP_DIR, LIVE_MAP_FILENAME)

    # Step 2: Compute initial positions, generate first map, open browser
    positions = _compute_all_positions(tle_cache, observer, get_satellite_position)
    _write_live_map(positions, observer, map_path, refresh_seconds)
    webbrowser.open(f"file:///{Path(map_path).as_posix()}")
    logger.info("Map Generator: Browser opened — entering live loop")

    # Step 3: Continuous update loop
    update_count = 1
    try:
        while True:
            time.sleep(refresh_seconds)
            update_count += 1
            positions = _compute_all_positions(tle_cache, observer, get_satellite_position)
            _write_live_map(positions, observer, map_path, refresh_seconds)
            logger.debug("Map Generator: Live update #%d", update_count)
    except KeyboardInterrupt:
        logger.info(
            "Map Generator: Live tracking stopped after %d updates",
            update_count,
        )


def _compute_all_positions(
    tle_cache: dict,
    observer: "ObserverLocation",
    get_position_fn,
) -> list[dict]:
    """Compute current positions for all satellites in the TLE cache.

    Args:
        tle_cache: Dict of norad_id → (name, tle_data).
        observer: Observer location model.
        get_position_fn: The get_satellite_position callable.

    Returns:
        List of position dicts, each augmented with a 'name' key.
    """
    positions = []
    for norad_id, (sat_name, tle_data) in tle_cache.items():
        try:
            pos = get_position_fn(tle_data, observer)
            pos["name"] = sat_name
            positions.append(pos)
        except Exception as exc:
            logger.warning(
                "Map Generator: Position computation failed for %s: %s",
                sat_name, exc,
            )
    return positions


def _write_live_map(
    positions: list[dict],
    observer: "ObserverLocation",
    map_path: str,
    refresh_seconds: int,
) -> None:
    """Build and save one frame of the live tracking map.

    Args:
        positions: List of satellite position dicts.
        observer: Observer location model.
        map_path: File path to write the HTML to.
        refresh_seconds: Auto-refresh interval for the <meta> tag.
    """
    sat_map = _build_satellite_map(
        satellites=positions,
        observer_lat=observer.latitude,
        observer_lon=observer.longitude,
        observer_city=observer.city,
        auto_refresh_seconds=refresh_seconds,
    )
    sat_map.save(map_path)
