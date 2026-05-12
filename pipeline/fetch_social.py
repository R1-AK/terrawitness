"""
TerraWitness social media ingest.
Fetches recent Twitter/X posts about nickel mining harm in Indonesia.
Merges results into public/incidents_live.json alongside RSS incidents.

Requires: requests, geopandas, shapely
Env: TWITTER_BEARER_TOKEN
"""

import json, hashlib, re, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import geopandas as gpd
from shapely.geometry import Point

ROOT      = Path(__file__).parent.parent
LEASES_GJ = ROOT / 'pipeline' / 'nickel_leases.geojson'
OUT_JSON  = ROOT / 'public'   / 'incidents_live.json'
SEEN_FILE = ROOT / 'pipeline' / 'seen_social.json'

BEARER = os.environ.get('TWITTER_BEARER_TOKEN', '')

SEARCH_QUERY = (
    '(nikel OR nickel OR tambang OR morowali OR halmahera OR weda OR konawe OR bombana) '
    '(limbah OR pencemaran OR cemari OR tercemar OR tailing OR illegal OR ilegal OR kerusakan) '
    'lang:id -is:retweet'
)

SEEN_TTL_DAYS = 7

# ── Same keyword sets as RSS pipeline ────────────────────────────────────────
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

# ── Witness credibility scoring ───────────────────────────────────────────────
# Higher score = more likely to be a genuine first-hand witness report

def witness_score(text: str, author_followers: int) -> float:
    norm = text.lower()
    score = 0.0

    # First-person language (+0.25)
    if re.search(r'\b(saya|kami|aku|kita|lihat|melihat|temukan|menemukan|laporkan)\b', norm):
        score += 0.25

    # Specific location mention (+0.20)
    if re.search(r'(desa|kecamatan|kabupaten|kampung|kelurahan|koordinat)', norm):
        score += 0.20

    # Media evidence words (+0.20)
    if re.search(r'(foto|video|gambar|rekaman|dokumentasi|bukti)', norm):
        score += 0.20

    # Specific harm description (+0.20)
    if re.search(r'(limbah|tailing|pencemaran|sedimen|keruh|mati|rusak|bau)', norm):
        score += 0.20

    # Credibility boost for accounts with some following (+0.15)
    if author_followers >= 100:
        score += 0.10
    if author_followers >= 1000:
        score += 0.05

    return round(min(score, 1.0), 2)


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


def fetch_tweets() -> list[dict]:
    """Call Twitter API v2 search/recent, return list of {id, text, created_at, author_followers, url}."""
    if not BEARER:
        print('  No TWITTER_BEARER_TOKEN — skipping social ingest')
        return []

    url = 'https://api.twitter.com/2/tweets/search/recent'
    headers = {'Authorization': f'Bearer {BEARER}'}
    params = {
        'query':       SEARCH_QUERY,
        'max_results': 100,
        'tweet.fields': 'created_at,author_id,public_metrics',
        'expansions':  'author_id',
        'user.fields': 'public_metrics',
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 429:
            print('  Twitter rate limit hit — skipping social ingest')
            return []
        if r.status_code != 200:
            print(f'  Twitter API error {r.status_code}: {r.text[:200]}')
            return []
        data = r.json()
    except Exception as e:
        print(f'  Twitter request failed: {e}')
        return []

    # Build author follower map
    followers: dict[str, int] = {}
    for user in data.get('includes', {}).get('users', []):
        followers[user['id']] = user.get('public_metrics', {}).get('followers_count', 0)

    tweets = []
    for t in data.get('data', []):
        tweets.append({
            'id':         t['id'],
            'text':       t.get('text', ''),
            'created_at': t.get('created_at', ''),
            'followers':  followers.get(t.get('author_id', ''), 0),
            'url':        f"https://twitter.com/i/web/status/{t['id']}",
        })

    print(f'  Fetched {len(tweets)} tweets from Twitter/X')
    return tweets


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f'[{datetime.now(timezone.utc).isoformat()}] Starting TerraWitness social ingest')

    gdf  = load_leases()
    seen = load_seen()

    existing: dict[str, dict] = {}
    if OUT_JSON.exists():
        for inc in json.loads(OUT_JSON.read_text()):
            existing[inc['id']] = inc

    tweets = fetch_tweets()
    new_count = 0

    for tweet in tweets:
        uid = article_id(tweet['url'])
        if uid in seen:
            continue
        seen[uid] = datetime.now(timezone.utc).isoformat()

        text = tweet['text']
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
        w_score      = witness_score(text, tweet['followers'])

        # Severity considers both distance and witness quality
        combined = round((change_score + w_score) / 2, 2)
        if combined > 0.75:
            severity = 'high'
        elif combined > 0.50:
            severity = 'medium'
        else:
            severity = 'low'

        try:
            dt = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')).isoformat()
        except Exception:
            dt = datetime.now(timezone.utc).isoformat()

        inc_id = f'TW-X-{uid.upper()}'

        incident = {
            'id':          inc_id,
            'status':      'geoparsing',
            'severity':    severity,
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
            'witness_score':     w_score,
            'ndvi_before':       0.0,
            'ndvi_after':        0.0,
            'area_ha':           0,
            'post_text':         re.sub(r'https?://\S+', '', text).strip()[:300],
            'post_date':         dt,
            'report_date':       dt[:10],
            'source_type':       'social_media',
            'source_name':       'Twitter/X',
            'source_url':        tweet['url'],
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
        print(f'    [NEW] {inc_id}  {kab}  {vtype}  score={w_score}  {text[:50]}')

    incidents = sorted(existing.values(), key=lambda x: x['post_date'], reverse=True)[:500]
    OUT_JSON.write_text(json.dumps(incidents, ensure_ascii=False, indent=2))
    save_seen(seen)
    print(f'\nDone. {new_count} new social incidents. {len(incidents)} total in {OUT_JSON}')


if __name__ == '__main__':
    run()
