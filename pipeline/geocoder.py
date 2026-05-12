"""
Geocoder: resolves Indonesian place names to (lat, lng) coordinates.

Priority order:
  1. Named geographic feature gazetteer (bays, rivers, named mining areas)
  2. Nominatim OSM search (kecamatan / kabupaten level)
  3. Nickel belt fallback gazetteer (known mining regions)
"""

import time
import requests

# Key named features in the East Indonesia nickel belt
FEATURE_GAZETTEER: dict[str, tuple[float, float]] = {
    "teluk buli":               (1.062,  127.764),
    "tanjung buli":             (1.031,  127.830),
    "moronopo":                 (1.120,  127.745),
    "sungai sagea":             (0.451,  127.562),
    "gua bokimaruru":           (0.420,  127.590),
    "sungai konaweha":          (-3.981, 122.457),
    "sungai lasolo":            (-3.612, 122.890),
    "das lasolo":               (-3.612, 122.890),
    "teluk kendari":            (-3.970, 122.598),
    "kabaena":                  (-5.282, 121.876),
    "pulau wawonii":            (-4.119, 123.099),
    "wawonii":                  (-4.119, 123.099),
    "morosi":                   (-4.021, 122.074),
    "morowali":                 (-2.525, 122.031),
}

# Kabupaten-level centroids for the nickel belt — fallback when Nominatim fails
KABUPATEN_GAZETTEER: dict[str, tuple[float, float]] = {
    "halmahera timur":          (0.872,  128.253),
    "halmahera tengah":         (0.468,  127.884),
    "halmahera utara":          (1.498,  127.798),
    "halmahera selatan":        (-0.682, 127.593),
    "halmahera barat":          (1.082,  127.539),
    "kepulauan sula":           (-1.890, 125.398),
    "pulau taliabu":            (-1.784, 124.758),
    "morowali":                 (-2.525, 122.031),
    "morowali utara":           (-1.856, 121.639),
    "konawe":                   (-4.045, 122.529),
    "konawe selatan":           (-4.267, 122.534),
    "konawe utara":             (-3.364, 122.201),
    "konawe kepulauan":         (-4.119, 123.099),
    "kolaka":                   (-4.056, 121.610),
    "kolaka timur":             (-4.198, 121.785),
    "bombana":                  (-4.818, 121.924),
}


def _normalize(text: str) -> str:
    return text.lower().strip()


def _try_feature_gazetteer(location: dict) -> tuple[float, float] | None:
    feature = location.get("feature_name", "") or ""
    for key, coords in FEATURE_GAZETTEER.items():
        if key in _normalize(feature):
            return coords
    return None


def _try_nominatim(location: dict) -> tuple[float, float] | None:
    """Try progressively broader queries until one returns a result."""
    queries = []

    # Build queries from specific → broad
    parts = []
    if location.get("kecamatan"):
        parts.append(location["kecamatan"])
    if location.get("kabupaten"):
        parts.append(location["kabupaten"])
    if location.get("provinsi"):
        parts.append(location["provinsi"])
    parts.append("Indonesia")

    # Try: kecamatan + kabupaten, then kabupaten alone, then feature name
    for i in range(len(parts)):
        queries.append(", ".join(parts[i:]))

    if location.get("feature_name"):
        queries.insert(0, f"{location['feature_name']}, Indonesia")

    headers = {"User-Agent": "TerraWitness/1.0 (academic research; contact: riska.kuswati96@gmail.com)"}

    for query in queries:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "id"},
                headers=headers,
                timeout=8,
            )
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
            time.sleep(1)  # Nominatim rate limit: 1 req/sec
        except Exception:
            continue

    return None


def _try_kabupaten_gazetteer(location: dict) -> tuple[float, float] | None:
    kab = _normalize(location.get("kabupaten", "") or "")
    for key, coords in KABUPATEN_GAZETTEER.items():
        if key in kab or kab in key:
            return coords
    return None


def geocode(location: dict) -> dict:
    """
    Resolve a location dict to coordinates.
    Returns the location dict with lat/lng added, plus a confidence level.

    location dict expected keys: desa, kecamatan, kabupaten, provinsi, feature_name
    """
    result = dict(location)

    coords = _try_feature_gazetteer(location)
    if coords:
        result["lat"], result["lng"] = coords
        result["geo_confidence"] = "feature"
        return result

    coords = _try_nominatim(location)
    if coords:
        result["lat"], result["lng"] = coords
        result["geo_confidence"] = "nominatim"
        return result

    coords = _try_kabupaten_gazetteer(location)
    if coords:
        result["lat"], result["lng"] = coords
        result["geo_confidence"] = "kabupaten_fallback"
        return result

    # Last resort: center of East Indonesia nickel belt
    result["lat"], result["lng"] = -1.5, 124.5
    result["geo_confidence"] = "region_fallback"
    return result
