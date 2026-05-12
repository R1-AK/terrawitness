"""
TerraWitness Telegram channel monitor.
Scrapes public Telegram channels for nickel mining harm posts.
No API key or token needed — uses t.me/s/{channel} public web view.

Channels monitored: JATAM, Mongabay, WALHI, Betahita, ForestDigest
"""

import json, hashlib, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import geopandas as gpd
from shapely.geometry import Point

ROOT      = Path(__file__).parent.parent
LEASES_GJ = ROOT / 'pipeline' / 'nickel_leases.geojson'
OUT_JSON  = ROOT / 'public'   / 'incidents_live.json'
SEEN_FILE = ROOT / 'pipeline' / 'seen_telegram.json'

SEEN_TTL_DAYS = 7

# Public Telegram channels covering Indonesian mining / environment
CHANNELS = [
    'jatamnas',        # JATAM Nasional — mining advocacy network
    'mongabayid',      # Mongabay Indonesia
    'walhinasional',   # WALHI — Friends of the Earth Indonesia
    'betahitaid',      # Betahita investigative journalism
    'forestdigestid',  # ForestDigest
]

# ── Same keyword sets as RSS + social pipelines ───────────────────────────────
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
COASTAL_KW = {'teluk','perairan','pantai','pesisir','laut','muara','bay',
               'nearshore','sedimentation','nelayan','terumbu','mangrove'}
RIVER_KW   = {'sungai','kali','hulu','hilir','aliran sungai','watershed',
               'upstream','downstream','river','keruh','turbid'}
VIOLATION_MAP = [
    ({'tailings','tailing','limbah cair','discharge','buang limbah'},         'tailings_discharge'),
    ({'illegal','ilegal','liar','tanpa izin','clearing','pembukaan lahan'},   'illegal_clearing'),
    ({'sungai','kali','air sungai','river','keruh','turbid'},                  'river_contamination'),
    ({'kawasan lindung','hutan lindung','konservasi','protected','cagar'},    'protected_area_breach'),
    ({'ekspansi','perluasan','melebihi batas','unauthorized','expansion'},    'unauthorized_expansion'),
]

KAB_GAZETTEER: dict[str, list[float]] = {}

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TerraWitness/1.0)'}

# ── Telegram scraper ──────────────────────────────────────────────────────────

def fetch_channel(channel: str) -> list[dict]:
    url = f'https://t.me/s/{channel}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f'  [{channel}] HTTP {r.status_code} — skipping')
            return []
        html = r.text
    except Exception as e:
        print(f'  [{channel}] Error: {e}')
        return []

    # t.me/s/ only works for public broadcast channels.
    # If Telegram returns a "Contact @..." page, the handle is a user/group, not a channel.
    if 'Telegram: Contact @' in html or 'tgme_widget_message' not in html:
        print(f'  [{channel}] Not a public broadcast channel — update CHANNELS list with correct handle')
        return []

    messages = []

    # Extract all data-post attributes, datetimes, and text blocks independently
    # then zip them — Telegram renders one of each per message in document order
    posts     = re.findall(r'data-post="([^"]+)"', html)
    datetimes = re.findall(r'<time[^>]+datetime="([^"]+)"', html)

    # Text: find all message text divs (class may include extra names like js-message_text)
    raw_texts = re.findall(
        r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )

    # Fallback: broader text extraction if the above misses
    if not raw_texts:
        raw_texts = re.findall(
            r'tgme_widget_message_text[^>]*>(.*?)</div>',
            html, re.DOTALL
        )

    print(f'  [{channel}] Parsing: {len(posts)} post blocks, {len(datetimes)} timestamps, {len(raw_texts)} text blocks')

    for i, post in enumerate(posts):
        text_raw = raw_texts[i] if i < len(raw_texts) else ''
        dt       = datetimes[i] if i < len(datetimes) else ''

        text = re.sub(r'<[^>]+>', ' ', text_raw)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 30:
            continue

        messages.append({
            'text':       text,
            'created_at': dt,
            'url':        f'https://t.me/{post}',
            'channel':    channel,
        })

    print(f'  [{channel}] {len(messages)} usable posts')
    return messages


# ── Shared pipeline helpers ───────────────────────────────────────────────────

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


def normalise(text: str) -> str:
    return text.lower() if text else ''


def article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def load_seen() -> dict:
    if not SEEN_FILE.exists():
        return {}
    data = json.loads(SEEN_FILE.read_text())
    if isinstance(data, list):
        data = {h: datetime.now(timezone.utc).isoformat() for h in data}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    return {h: ts for h, ts in data.items() if ts >= cutoff}


def save_seen(seen: dict):
    SEEN_FILE.write_text(json.dumps(seen, separators=(',', ':')))


def is_relevant(text: str) -> bool:
    norm = normalise(text)
    return any(k in norm for k in MINING_KW) and any(k in norm for k in HARM_KW)


def extract_location(text: str):
    norm = normalise(text)
    desa = kec = kab = None

    m = re.search(r'desa\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: desa = m.group(1).strip()

    m = re.search(r'kecamatan\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: kec = m.group(1).strip()

    m = re.search(r'kabupaten\s+([a-z][a-z\s\-]{2,30}?)(?:\s|,|\.)', norm)
    if m: kab = m.group(1).strip()

    if not kab:
        for k in sorted(KAB_GAZETTEER.keys(), key=len, reverse=True):
            if ',' not in k and k in norm:
                kab = k
                break

    lat = lng = None
    if kab and kab in KAB_GAZETTEER:
        lat, lng = KAB_GAZETTEER[kab]
    elif kab:
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


def nearest_lease(gdf, lat: float, lng: float):
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


def channel_display_name(channel: str) -> str:
    names = {
        'jatamnas':     'JATAM Nasional',
        'mongabayid':   'Mongabay Indonesia',
        'walhinasional':'WALHI',
        'betahitaid':   'Betahita',
        'forestdigestid':'ForestDigest',
    }
    return names.get(channel, channel)


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f'[{datetime.now(timezone.utc).isoformat()}] Starting TerraWitness Telegram ingest')

    gdf  = load_leases()
    seen = load_seen()

    existing: dict[str, dict] = {}
    if OUT_JSON.exists():
        for inc in json.loads(OUT_JSON.read_text()):
            existing[inc['id']] = inc

    new_count = 0

    for channel in CHANNELS:
        posts = fetch_channel(channel)

        for post in posts:
            uid = article_id(post['url'])
            if uid in seen:
                continue
            seen[uid] = datetime.now(timezone.utc).isoformat()

            text = post['text']
            if not is_relevant(text):
                continue

            kab, kec, desa, lat, lng = extract_location(text)
            if lat is None or lng is None:
                print(f'    [no location] {text[:60]}')
                continue

            lease = nearest_lease(gdf, lat, lng)
            if not lease or lease['dist_km'] > 80:
                print(f'    [no nearby lease] {text[:60]}')
                continue

            signal_type  = classify_signal(text)
            vtype        = classify_violation(text)
            change_score = round(max(0.3, min(0.95, 1.0 - lease['dist_km'] / 100)), 2)

            try:
                dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).isoformat()
            except Exception:
                dt = datetime.now(timezone.utc).isoformat()

            inc_id = f'TW-TG-{uid.upper()}'

            incident = {
                'id':          inc_id,
                'status':      'geoparsing',
                'severity':    'medium' if change_score > 0.5 else 'low',
                'location': {
                    'lat':       lat,
                    'lng':       lng,
                    'desa':      desa or '-',
                    'kecamatan': kec  or '-',
                    'kabupaten': kab  or '-',
                    'provinsi':  '-',
                },
                'violation_type':    vtype,
                'zone_name':         f'{kab} {signal_type} zone' if kab else 'Unknown zone',
                'zone_type':         signal_type,
                'violation_flag':    True,
                'change_score':      change_score,
                'ndvi_before':       0.0,
                'ndvi_after':        0.0,
                'area_ha':           0,
                'post_text':         text[:300],
                'post_date':         dt,
                'report_date':       dt[:10],
                'source_type':       'social_media',
                'source_name':       channel_display_name(post['channel']),
                'source_url':        post['url'],
                'source_date':       dt[:10],
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
            print(f'    [NEW] {inc_id}  {kab}  {vtype}  {text[:50]}')

    incidents = sorted(existing.values(), key=lambda x: x['post_date'], reverse=True)[:500]
    OUT_JSON.write_text(json.dumps(incidents, ensure_ascii=False, indent=2))
    save_seen(seen)
    print(f'\nDone. {new_count} new Telegram incidents. {len(incidents)} total in {OUT_JSON}')


if __name__ == '__main__':
    run()
