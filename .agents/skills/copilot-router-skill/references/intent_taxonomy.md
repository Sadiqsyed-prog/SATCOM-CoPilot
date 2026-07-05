# Intent Taxonomy Reference

## Satellite Alias Resolution Table

| User Input (case-insensitive) | Official Catalog Name | NORAD ID | Notes |
|------------------------------|----------------------|----------|-------|
| ISS, International Space Station, Space Station, Zarya | ISS (ZARYA) | 25544 | **Default target** |
| Hubble, HST, Hubble Telescope, Hubble Space Telescope | HST | 20580 | Low-Earth orbit |
| Tiangong, Chinese Space Station, CSS, Tianhe | CSS (TIANHE) | 48274 | Chinese station |
| GOES-16, GOES East, GOES 16 | GOES 16 | 41866 | Geostationary |
| Starlink | (multiple) | (varies) | Requires constellation handling |
| Landsat 9, Landsat | LANDSAT 9 | 49260 | Earth observation |
| James Webb, JWST | JWST | 50463 | L2 orbit (limited tracking) |

## Intent Classification Patterns

### TRACK_PASS
Keywords: `pass`, `passes`, `passing`, `fly over`, `flyover`, `overhead`, `when`
Pattern: `[when/what time] + [satellite] + [pass/fly] + [over/above] + [location]`
Examples:
- "When does ISS pass over Bengaluru?"
- "Show me all Hubble passes over London this week"
- "What time does the space station fly over New York?"

### SATELLITE_POSITION
Keywords: `where`, `position`, `location`, `right now`, `currently`, `live`
Pattern: `[where] + [satellite] + [now/currently]`
Examples:
- "Where is the ISS right now?"
- "Current position of Hubble?"
- "Show me ISS live location"

### VISIBILITY_CHECK
Keywords: `see`, `visible`, `watch`, `observe`, `view`, `spot`, `visibility`
Pattern: `[can I see/is...visible] + [satellite] + [from location]`
Examples:
- "Can I see the ISS from Mumbai tonight?"
- "Is Hubble visible from Delhi?"
- "Best time to observe ISS from Tokyo?"

### HELP
Keywords: `help`, `what can you`, `capabilities`, `commands`, `how to`, `usage`
Examples:
- "What can you do?"
- "Help"
- "Show me available commands"

### UNKNOWN
Fallback when no pattern matches. Return usage guidance template.

## Time Window Resolution

| Expression | Resolution |
|-----------|-----------|
| tonight | Current time → next 06:00 local |
| tomorrow | Next midnight → +24h local |
| today | Current time → midnight local |
| this week | Current time → +168h |
| next N days | Current time → +(N×24)h |
| next N hours | Current time → +Nh |
| (unspecified) | Current time → +72h (default) |
