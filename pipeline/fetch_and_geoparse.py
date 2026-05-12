"""
TerraWitness auto-ingestion pipeline.
Runs on GitHub Actions every 2 hours (free).

Steps:
  1. Fetch RSS feeds (Mongabay, Betahita, Kompas, Tempo, Antara, CNN, Detik)
  2. Filter for nickel / mining / environmental harm keywords
  3. Regex geoparse -> extract kabupaten/kecamatan/desa + water-body keywords
  4. Look up coordinates from WIUP-derived kabupaten gazetteer
  5. Spatial match to nearest nickel lease (nickel_leases.geojson)
  6. Classify signal type (teluk/river/coastal/land) from text keywords
  7. Write public/incidents_live.json  (read by the frontend)

Requires: feedparser, shapely, geopandas  (all free, pip install)
"""

import json, hashlib, re, os, sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import geopandas as gpd
from shapely.geometry import Point

# ── Paths (relative to repo root, for GitHub Actions) ────────────────────────
ROOT       = Path(__file__).parent.parent
LEASES_GJ  = ROOT / 'pipeline' / 'nickel_leases.geojson'
OUT_JSON   = ROOT / 'public'   / 'incidents_live.json'
SEEN_FILE  = ROOT / 'pipeline' / 'seen_hashes.json'

# ── RSS feeds ─────────────────────────────────────────────────────────────────
FEEDS = [
    'https://www.mongabay.co.id/feed/',
    'https://betahita.id/feed',
    'https://www.forestdigest.com/feed',
    'https://www.kompas.com/tag/nikel.rss',
    'https://rss.tempo.co/nasional',
    'https://www.antaranews.com/rss/topnews.xml',
    'https://www.cnnindonesia.com/ekonomi/rss',
    'https://www.detik.com/tag/nikel/rss',
]

# ── Mining + harm keywords (must appear in title or summary) ──────────────────
MINING_KW = {
    'nikel','nickel','tambang','pertambangan','smelter','imip','iwip',
    'weda','morowali','halmahera','konawe','bombana','raja ampat','wawonii',
    'kao','buli','kabaena','lasolo','sagea',
}
HARM_KW = {
    'limbah','pencemaran','cemari','tercemar','sedimen','keruh','rusak',
    'tailing','discharge','contamina','pollution','deforestation','clearing',
    'banjir lumpur','tumpahan','illegal','ilegal','kerusakan lingkungan',
}

# ── Spatial context keywords ──────────────────────────────────────────────────
COASTAL_KW = {'teluk','perairan','pantai','pesisir','laut','muara','bay',
               'nearshore','sedimentation','nelayan','terumbu','mangrove'}
RIVER_KW   = {'sungai','kali','hulu','hilir','aliran sungai','daerah aliran',
               'watershed','upstream','downstream','river','keruh','turbid'}

# ── Violation type heuristics ─────────────────────────────────────────────────
VIOLATION_MAP = [
    ({'tailings','tailing','limbah cair','discharge','buang limbah'},         'tailings_discharge'),
    ({'illegal','ilegal','liar','tanpa izin','clearing','pembukaan lahan'},   'illegal_clearing'),
    ({'sungai','kali','air sungai','river','keruh','turbid'},                  'river_contamination'),
    ({'kawasan lindung','hutan lindung','konservasi','protected','cagar'},    'protected_area_breach'),
    ({'ekspansi','perluasan','melebihi batas','unauthorized','expansion'},    'unauthorized_expansion'),
]

# ── Kabupaten gazetteer (built from WIUP centroids) ───────────────────────────
# Normalised lowercase name -> [lat, lng]
KAB_GAZETTEER: dict[str, list[float]] = {}

def load_leases():
    gdf = gpd.read_file(LEASES_GJ)
    seen: set[str] = set()
    for _, row in gdf.iterrows():
        kab = str(row.get('nama_kab', '') or '').strip().lower()
        if kab and kab not in seen:
            c = row['geometry'].centroid
            KAB_GAZETTEER[kab] = [round(c.y, 4), round(c.x, 4)]
            seen.add(kab)
    return gdf

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise(text: str) -> str:
    return text.lower() if text else ''

def article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(sorted(seen)))

def is_relevant(title: str, summary: str) -> bool:
    text = normalise(f'{title} {summary}')
    has_mining = any(k in text for k in MINING_KW)
    has_harm   = any(k in text for k in HARM_KW)
    return has_mining and has_harm

def extract_location(text: str) -> tuple[str | None, str | None, str | None, float | None, float | None]:
    """Return (kabupaten, kecamatan, desa, lat, lng)."""
    norm = normalise(text)

    # Try desa / kecamatan / kabupaten patterns
    desa  = None
    kec   = None
    kab   = None

    m = re.search(r'desa\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: desa = m.group(1).strip()

    m = re.search(r'kecamatan\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: kec = m.group(1).strip()

    m = re.search(r'kabupaten\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: kab = m.group(1).strip()

    # Direct mention of known kabupaten without the word "kabupaten"
    if not kab:
        for k in sorted(KAB_GAZETTEER.keys(), key=len, reverse=True):
            # Only single-kabupaten keys (no comma)
            if ',' not in k and k in norm:
                kab = k
                break

    # Look up coordinates
    lat = lng = None
    if kab and kab in KAB_GAZETTEER:
        lat, lng = KAB_GAZETTEER[kab]
    elif kab:
        # Fuzzy: find best partial match
        for k, coords in KAB_GAZETTEER.items():
            if kab in k or k in kab:
                lat, lng = coords
                break

    return kab, kec, desa, lat, lng

def classify_signal(text: str) -> str:
    norm = normalise(text)
    words = set(norm.split())
    if words & COASTAL_KW:
        return 'teluk' if re.search(r'teluk\s+\w+', norm) else 'coastal'
    if words & RIVER_KW:
        return 'river'
    return 'land'

def classify_violation(text: str) -> str:
    norm = normalise(text)
    for keywords, vtype in VIOLATION_MAP:
        if any(k in norm for k in keywords):
            return vtype
    return 'illegal_clearing'

def classify_severity(text: str, change_score: float) -> str:
    norm = normalise(text)
    critical_kw = {'kritis','fatal','mati','maut','darurat','emergency','krisis'}
    if change_score > 0.85 or any(k in norm for k in critical_kw):
        return 'critical'
    if change_score > 0.65:
        return 'high'
    if change_score > 0.45:
        return 'medium'
    return 'low'

def nearest_lease(gdf, lat: float, lng: float) -> dict | None:
    pt = Point(lng, lat)
    gdf = gdf.copy()
    gdf['_dist'] = gdf.geometry.distance(pt)
    row = gdf.nsmallest(1, '_dist').iloc[0]
    c = row.geometry.centroid
    return {
        'lease_name': str(row['nama_usaha']).strip(),
        'komoditas':  str(row['komoditas']).strip(),
        'kegiatan':   str(row['kegiatan']).strip(),
        'luas_ha':    float(row['luas_sk']) if row['luas_sk'] else 0,
        'centroid':   [round(c.y, 5), round(c.x, 5)],
        'dist_km':    round(row['_dist'] * 111, 1),
    }

def source_type_from_url(url: str) -> str:
    domain = url.lower()
    if 'mongabay' in domain or 'betahita' in domain or 'forestdigest' in domain:
        return 'investigation'
    if 'kompas' in domain or 'tempo' in domain or 'antara' in domain:
        return 'national_news'
    if 'cnn' in domain or 'detik' in domain or 'kumparan' in domain:
        return 'national_news'
    return 'local_news'

def source_name_from_url(url: str) -> str:
    for name, frag in [
        ('Mongabay Indonesia','mongabay'),
        ('Betahita','betahita'),
        ('ForestDigest','forestdigest'),
        ('Kompas','kompas'),
        ('Tempo','tempo'),
        ('Antara News','antara'),
        ('CNN Indonesia','cnn'),
        ('Detik','detik'),
        ('Kumparan','kumparan'),
    ]:
        if frag in url.lower():
            return name
    return 'Unknown'

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f'[{datetime.now(timezone.utc).isoformat()}] Starting TerraWitness geoparse pipeline')

    gdf  = load_leases()
    seen = load_seen()

    # Load existing live incidents (merge, not overwrite)
    existing: dict[str, dict] = {}
    if OUT_JSON.exists():
        for inc in json.loads(OUT_JSON.read_text()):
            existing[inc['id']] = inc

    new_count = 0

    for feed_url in FEEDS:
        print(f'  Fetching {feed_url}')
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f'    Error: {e}')
            continue

        for entry in feed.entries:
            url     = entry.get('link', '')
            title   = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            pub     = entry.get('published', entry.get('updated', ''))

            uid = article_id(url)
            if uid in seen:
                continue
            seen.add(uid)

            if not is_relevant(title, summary):
                continue

            text = f'{title}. {summary}'
            kab, kec, desa, lat, lng = extract_location(text)

            if lat is None or lng is None:
                print(f'    [no location] {title[:60]}')
                continue

            lease = nearest_lease(gdf, lat, lng)
            if not lease or lease['dist_km'] > 80:
                print(f'    [no nearby lease] {title[:60]}')
                continue

            signal_type = classify_signal(text)
            vtype       = classify_violation(text)
            # Rough change score proxy: inverse of lease distance, capped
            change_score = round(max(0.3, min(0.95, 1.0 - lease['dist_km'] / 100)), 2)
            severity     = classify_severity(text, change_score)

            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub).isoformat()
            except Exception:
                dt = datetime.now(timezone.utc).isoformat()

            inc_id = f'TW-AUTO-{uid.upper()}'

            incident = {
                'id':           inc_id,
                'status':       'geoparsing',
                'severity':     severity,
                'location': {
                    'lat':       lat,
                    'lng':       lng,
                    'desa':      desa or '-',
                    'kecamatan': kec  or '-',
                    'kabupaten': kab  or '-',
                    'provinsi':  '-',
                },
                'violation_type':  vtype,
                'zone_name':       f'{kab} {signal_type} zone' if kab else 'Unknown zone',
                'zone_type':       signal_type,
                'violation_flag':  True,
                'change_score':    change_score,
                'ndvi_before':     0.0,
                'ndvi_after':      0.0,
                'area_ha':         0,
                'post_text':       re.sub('<[^>]+>', '', summary)[:300].strip(),
                'post_date':       dt,
                'report_date':     dt[:10],
                'source_type':     source_type_from_url(url),
                'source_name':     source_name_from_url(url),
                'source_url':      url,
                'source_date':     dt[:10],
                'concession_holder': lease['lease_name'] if 'PT' in lease['lease_name'].upper() else None,
                'lease_match': {
                    'name':      lease['lease_name'],
                    'activity':  lease['kegiatan'],
                    'commodity': lease['komoditas'],
                    'area_ha':   lease['luas_ha'],
                    'dist_km':   lease['dist_km'],
                    'centroid':  lease['centroid'],
                },
                'signal_type': signal_type,
            }

            existing[inc_id] = incident
            new_count += 1
            print(f'    [NEW] {inc_id}  {kab}  {vtype}  {title[:50]}')

    # Sort by date descending, keep latest 200
    incidents = sorted(existing.values(), key=lambda x: x['post_date'], reverse=True)[:200]

    OUT_JSON.write_text(json.dumps(incidents, ensure_ascii=False, indent=2))
    save_seen(seen)
    print(f'\nDone. {new_count} new incidents. {len(incidents)} total in {OUT_JSON}')

if __name__ == '__main__':
    run()
