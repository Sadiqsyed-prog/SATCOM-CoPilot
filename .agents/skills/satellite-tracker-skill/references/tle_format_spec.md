# TLE (Two-Line Element) Format Specification

## Overview
A Two-Line Element set (TLE) is a standardized data format encoding orbital
parameters for Earth-orbiting objects. TLEs are designed specifically for use
with the SGP4/SDP4 propagation models — they must NOT be used with other propagators.

## Format Structure

```
Line 0:  ISS (ZARYA)                          ← Satellite name (optional)
Line 1:  1 25544U 98067A   26182.50000000  .00016717  00000-0  10270-3 0  9025
Line 2:  2 25544  51.6400 200.1234 0007500  50.1234 310.5678 15.48919755123456
```

## Line 1 Field Breakdown (69 characters)

| Column | Field | Example | Description |
|--------|-------|---------|-------------|
| 01 | Line Number | `1` | Always "1" |
| 03-07 | Catalog Number | `25544` | NORAD catalog number |
| 08 | Classification | `U` | U=Unclassified, C=Classified, S=Secret |
| 10-17 | Intl Designator | `98067A` | Launch year (98), launch number (067), piece (A) |
| 19-32 | Epoch | `26182.50000000` | Year (26=2026) + day of year with fraction |
| 34-43 | 1st Derivative | `.00016717` | Mean motion derivative (rev/day²) ÷ 2 |
| 45-52 | 2nd Derivative | `00000-0` | Mean motion 2nd derivative (rev/day³) ÷ 6 |
| 54-61 | BSTAR Drag | `10270-3` | B* drag term (1/Earth radii) |
| 63 | Ephemeris Type | `0` | Always 0 for SGP4 |
| 65-68 | Element Number | `902` | Sequential element set number |
| 69 | Checksum | `5` | Modulo 10 checksum |

## Line 2 Field Breakdown (69 characters)

| Column | Field | Example | Unit | Description |
|--------|-------|---------|------|-------------|
| 01 | Line Number | `2` | — | Always "2" |
| 03-07 | Catalog Number | `25544` | — | Must match Line 1 |
| 09-16 | Inclination | `51.6400` | degrees | Orbital inclination |
| 18-25 | RAAN | `200.1234` | degrees | Right Ascension of Ascending Node |
| 27-33 | Eccentricity | `0007500` | — | Decimal assumed (= 0.0007500) |
| 35-42 | Arg of Perigee | `50.1234` | degrees | Argument of perigee |
| 44-51 | Mean Anomaly | `310.5678` | degrees | Mean anomaly |
| 53-63 | Mean Motion | `15.48919755` | rev/day | Revolutions per day |
| 64-68 | Rev Number | `12345` | — | Revolution count at epoch |
| 69 | Checksum | `6` | — | Modulo 10 checksum |

## Checksum Algorithm

```python
def tle_checksum(line: str) -> int:
    """Compute modulo-10 checksum for a TLE line."""
    total = 0
    for char in line[:68]:  # Exclude the checksum digit itself
        if char.isdigit():
            total += int(char)
        elif char == '-':
            total += 1
        # All other characters (letters, spaces, '.', '+') = 0
    return total % 10
```

## Epoch Conversion

```python
def parse_tle_epoch(epoch_str: str) -> datetime:
    """Convert TLE epoch string to datetime.
    
    Format: YYDDD.DDDDDDDD
    YY = 2-digit year (00-56 = 2000-2056, 57-99 = 1957-1999)
    DDD.DDDDDDDD = day of year with fractional day
    """
    year_2d = int(epoch_str[:2])
    year = 2000 + year_2d if year_2d < 57 else 1900 + year_2d
    day_of_year = float(epoch_str[2:])
    return datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
```

## ISS Reference Orbital Parameters

| Parameter | Typical Value | Range |
|-----------|--------------|-------|
| Inclination | ~51.64° | 51.6° ± 0.1° |
| Eccentricity | ~0.0007 | Near-circular |
| Mean Motion | ~15.49 rev/day | 15.4–15.6 |
| Orbital Period | ~92.68 min | ~92–93 min |
| Altitude | ~408–420 km | Low Earth Orbit |
| Orbital Speed | ~7.66 km/s | — |
