"""
TerraWitness — Satellite-derived signal point computation.

Pipeline for any incident:
  Step 1  Lease lookup
          Find the WIUP nickel lease polygon nearest to the incident's
          approximate location in nickel_leases.geojson.

  Step 2  Sentinel-2 BSI (Bare Soil Index)
          Fetch Sentinel-2 L2A imagery over the lease from Planetary Computer.
          BSI = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))
          High BSI = bare soil / active open-pit mine.
          Centroid of top-15% BSI pixels = actual mining footprint centre.

  Step 3  Signal placement
          land    -> BSI centroid directly
          coastal -> snap BSI centroid to nearest OSM coastline segment
          teluk   -> nearest point on named OSM bay geometry
          river   -> OSM river segment downstream of BSI centroid

  Writes the result to public/incident_signals.json.

Usage:
  python pipeline/compute_signal_from_satellite.py \\
      --id TW-X-GECKO001 \\
      --lat -1.47 --lng 127.43 \\
      --signal coastal \\
      --hint harita
"""

import argparse, json, time, warnings
import numpy as np
import requests
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds, transform as warp_transform
from shapely.geometry import Point, Polygon, LineString, mapping
from shapely.ops import nearest_points, unary_union
from pathlib import Path

import pystac_client, planetary_computer

warnings.filterwarnings('ignore')

ROOT         = Path(__file__).parent.parent
LEASES_GJ    = ROOT / 'pipeline' / 'nickel_leases.geojson'
SIGNALS_JSON = ROOT / 'public'   / 'incident_signals.json'

OVERPASS_ENDPOINTS = [
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass-api.de/api/interpreter',
]

TOP_PCT      = 0.85   # top 15% highest BSI = active mining pixels
MIN_VALID_PX = 4


# ── Step 1: Lease lookup ──────────────────────────────────────────────────────

def find_nearest_lease(gdf, lat: float, lng: float, hint: str = '') -> tuple:
    """
    Return (row, polygon) for the WIUP lease closest to (lat, lng).
    If hint is given, filter to leases whose name contains the hint string
    before distance ranking — useful when you know the operator name.
    """
    pt = Point(lng, lat)
    candidates = gdf.copy()

    if hint:
        mask = candidates['nama_usaha'].str.lower().str.contains(hint.lower(), na=False)
        if mask.sum() > 0:
            candidates = candidates[mask]
            print(f'  Hint "{hint}" matched {len(candidates)} lease(s)')
        else:
            print(f'  Hint "{hint}" matched nothing — searching all {len(candidates)} leases')

    candidates = candidates.copy()
    candidates['_dist'] = candidates.geometry.distance(pt)
    row = candidates.nsmallest(1, '_dist').iloc[0]
    poly = row.geometry
    print(f'  Nearest lease: {row["nama_usaha"]}  '
          f'({row.get("kabupaten","?")} / {row.get("nama_kab","?")})  '
          f'dist={round(row["_dist"]*111,1)} km')
    return row, poly


# ── Step 2: Sentinel-2 BSI ────────────────────────────────────────────────────

catalog = pystac_client.Client.open(
    'https://planetarycomputer.microsoft.com/api/stac/v1',
    modifier=planetary_computer.sign_inplace,
)


def read_band_window(href, bbox_4326):
    with rasterio.open(href) as src:
        crs = src.crs
        bbox = transform_bounds('EPSG:4326', crs, *bbox_4326) if crs.to_epsg() != 4326 else bbox_4326
        win  = from_bounds(*bbox, transform=src.transform)
        win  = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        h    = max(1, int(round(abs(win.height))))
        w    = max(1, int(round(abs(win.width))))
        data = src.read(1, window=win, out_shape=(h, w),
                        resampling=Resampling.bilinear).astype(float)
        t    = src.window_transform(win)
    return data, t, crs


def build_coord_grid(t, H, W, crs):
    rows = np.arange(H) + 0.5
    cols = np.arange(W) + 0.5
    COL, ROW = np.meshgrid(cols, rows)
    X = t.c + COL * t.a + ROW * t.b
    Y = t.f + COL * t.d + ROW * t.e
    if crs.to_epsg() != 4326:
        flat_lons, flat_lats = warp_transform(
            crs, 'EPSG:4326', X.ravel().tolist(), Y.ravel().tolist())
        LON = np.array(flat_lons).reshape(H, W)
        LAT = np.array(flat_lats).reshape(H, W)
    else:
        LON, LAT = X, Y
    return LON, LAT


def resize_band(a, H, W):
    if a.shape == (H, W):
        return a
    row_idx = np.minimum((np.arange(H) * a.shape[0] / H).astype(int), a.shape[0] - 1)
    col_idx = np.minimum((np.arange(W) * a.shape[1] / W).astype(int), a.shape[1] - 1)
    return a[np.ix_(row_idx, col_idx)]


def compute_bsi_centroid(poly: Polygon) -> list[float] | None:
    """
    Run Sentinel-2 BSI over the lease polygon.
    Returns [lat, lng] of the bare-soil centroid or None if no scene found.
    """
    b   = poly.bounds   # minx, miny, maxx, maxy (lng, lat)
    buf = 0.005
    bbox_4326   = (b[0] - buf, b[1] - buf, b[2] + buf, b[3] + buf)
    poly_geojson = mapping(poly)

    items = []
    for date_range, max_cloud in [
        ('2023-01-01/2024-12-31', 15),
        ('2021-01-01/2024-12-31', 25),
        ('2019-01-01/2024-12-31', 40),
    ]:
        if items:
            break
        try:
            search = catalog.search(
                collections=['sentinel-2-l2a'],
                intersects=poly_geojson,
                datetime=date_range,
                query={'eo:cloud_cover': {'lt': max_cloud}},
                sortby=[{'field': 'eo:cloud_cover', 'direction': 'asc'}],
                limit=5,
            )
            items = list(search.items())
        except Exception as e:
            print(f'  STAC search error: {e}')

    if not items:
        print('  No Sentinel-2 scenes found')
        return None

    for item in items[:5]:
        cc = item.properties.get('eo:cloud_cover', '?')
        dt = item.properties.get('datetime', '?')[:10]
        print(f'  Scene: {item.id[:42]}  cloud={cc}%  {dt}')

        assets = item.assets
        hrefs  = {k: assets[k].href for k in ['B02','B04','B08','B11'] if k in assets}
        if len(hrefs) < 4:
            print('  Missing bands — skip')
            continue

        try:
            red,   t_ref, crs = read_band_window(hrefs['B04'], bbox_4326)
            blue,  _,     _   = read_band_window(hrefs['B02'], bbox_4326)
            nir,   _,     _   = read_band_window(hrefs['B08'], bbox_4326)
            swir1, _,     _   = read_band_window(hrefs['B11'], bbox_4326)
        except Exception as e:
            print(f'  Read error: {e}')
            continue

        H, W = red.shape
        if H < 2 or W < 2:
            continue

        blue  = resize_band(blue,  H, W)
        nir   = resize_band(nir,   H, W)
        swir1 = resize_band(swir1, H, W)

        denom = (swir1 + red) + (nir + blue)
        denom = np.where(denom == 0, np.nan, denom)
        bsi   = ((swir1 + red) - (nir + blue)) / denom

        LON, LAT = build_coord_grid(t_ref, H, W, crs)

        # Mask to lease polygon
        in_poly     = np.vectorize(lambda lo, la: poly.contains(Point(lo, la)))(LON, LAT)
        bsi_masked  = np.where(in_poly, bsi, np.nan)
        valid       = np.isfinite(bsi_masked)
        n_valid     = int(valid.sum())

        if n_valid < MIN_VALID_PX:
            print(f'  Only {n_valid} valid pixels in polygon — skip')
            continue

        vals = bsi_masked[valid]
        thr  = np.percentile(vals, TOP_PCT * 100)
        hot  = (bsi_masked >= thr) & valid
        n_hot = int(hot.sum())

        print(f'  BSI min={vals.min():.3f}  max={vals.max():.3f}  thr={thr:.3f}')
        print(f'  Bare-soil pixels: {n_hot}/{n_valid}')

        if n_hot == 0:
            continue

        bsi_lat = float(np.median(LAT[hot]))
        bsi_lng = float(np.median(LON[hot]))
        print(f'  BSI centroid: {bsi_lat:.5f}, {bsi_lng:.5f}')
        return [round(bsi_lat, 5), round(bsi_lng, 5)]

    return None


# ── Step 3: OSM coastal / river snap ─────────────────────────────────────────

def overpass_query(query: str) -> list:
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.get(endpoint, params={'data': query}, timeout=35,
                             headers={'Accept': 'application/json'})
            r.raise_for_status()
            data  = r.json()
            geoms = []
            for elem in data.get('elements', []):
                if elem.get('type') == 'way' and 'geometry' in elem:
                    coords = [(g['lon'], g['lat']) for g in elem['geometry']]
                    if len(coords) >= 2:
                        geoms.append(LineString(coords))
                elif elem.get('type') == 'relation':
                    outer = []
                    for m in elem.get('members', []):
                        if m.get('role') == 'outer' and 'geometry' in m:
                            outer.extend([(g['lon'], g['lat']) for g in m['geometry']])
                    if len(outer) >= 3:
                        geoms.append(Polygon(outer))
            if geoms:
                print(f'  OSM: {len(geoms)} features from {endpoint.split("/")[2]}')
                return geoms
        except Exception as e:
            print(f'  OSM error ({endpoint.split("/")[2]}): {e}')
        time.sleep(1)
    return []


def snap_to_coastline(bsi_lat: float, bsi_lng: float, search_radius_deg: float = 0.3) -> list[float] | None:
    """Query OSM coastline near the BSI centroid and return nearest shoreline point."""
    lat, lng = bsi_lat, bsi_lng
    query = (
        f'[out:json][timeout:30];'
        f'(way(around:{int(search_radius_deg*111000)},{lat},{lng})[natural="coastline"];);'
        f'out geom;'
    )
    print(f'  Querying OSM coastline within {search_radius_deg*111:.0f} km of BSI centroid...')
    geoms = overpass_query(query)

    if not geoms:
        print('  No OSM coastline found')
        return None

    merged   = unary_union(geoms)
    mine_pt  = Point(lng, lat)
    coast_pt, _ = nearest_points(merged, mine_pt)
    result = [round(coast_pt.y, 5), round(coast_pt.x, 5)]
    print(f'  Nearest coastline point: {result[0]}, {result[1]}')
    return result


def snap_to_river(bsi_lat: float, bsi_lng: float, search_radius_deg: float = 0.25) -> list[float] | None:
    lat, lng = bsi_lat, bsi_lng
    query = (
        f'[out:json][timeout:30];'
        f'(way(around:{int(search_radius_deg*111000)},{lat},{lng})'
        f'[waterway~"^(river|stream)$"];);out geom;'
    )
    print(f'  Querying OSM rivers within {search_radius_deg*111:.0f} km of BSI centroid...')
    geoms = overpass_query(query)

    if not geoms:
        return None

    center = Point(lng, lat)
    # Pick river point slightly downstream (away from mine centroid)
    merged   = unary_union(geoms)
    near_pt, _ = nearest_points(merged, center)

    # Find the endpoint of a river LineString that is furthest from the mine
    endpoints = []
    for g in geoms:
        if isinstance(g, LineString):
            endpoints += [Point(g.coords[0]), Point(g.coords[-1])]

    if endpoints:
        far = max(endpoints, key=lambda p: p.distance(center))
        # Blend: 55% downstream endpoint, 45% nearest river point
        lng_out = 0.55 * far.x + 0.45 * near_pt.x
        lat_out = 0.55 * far.y + 0.45 * near_pt.y
        result  = [round(lat_out, 5), round(lng_out, 5)]
    else:
        result = [round(near_pt.y, 5), round(near_pt.x, 5)]

    print(f'  River signal point: {result[0]}, {result[1]}')
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Compute satellite-derived signal point')
    parser.add_argument('--id',     required=True,  help='Incident ID, e.g. TW-X-GECKO001')
    parser.add_argument('--lat',    required=True,  type=float, help='Approx latitude')
    parser.add_argument('--lng',    required=True,  type=float, help='Approx longitude')
    parser.add_argument('--signal', required=True,  choices=['land','coastal','teluk','river'],
                        help='Signal type')
    parser.add_argument('--hint',   default='',     help='Operator name hint to filter leases')
    parser.add_argument('--label',  default='',     help='Human-readable label for the signal point')
    args = parser.parse_args()

    print(f'\n=== TerraWitness signal computation for {args.id} ===')
    print(f'Approx location: {args.lat}, {args.lng}  |  signal_type: {args.signal}')

    # Step 1 — Find lease
    print('\n[Step 1] Finding nearest WIUP lease...')
    gdf = gpd.read_file(LEASES_GJ)
    row, lease_poly = find_nearest_lease(gdf, args.lat, args.lng, args.hint)

    # Step 2 — BSI centroid from Sentinel-2
    print('\n[Step 2] Computing BSI bare-soil centroid from Sentinel-2...')
    bsi_centroid = compute_bsi_centroid(lease_poly)

    if bsi_centroid is None:
        print('  BSI failed — falling back to lease polygon centroid')
        c = lease_poly.centroid
        bsi_centroid = [round(c.y, 5), round(c.x, 5)]
        bsi_source = 'polygon_centroid'
    else:
        bsi_source = 'bsi'

    print(f'  Mining area centroid: {bsi_centroid[0]}, {bsi_centroid[1]}  [{bsi_source}]')

    # Step 3 — Signal placement
    print(f'\n[Step 3] Placing signal point (type={args.signal})...')
    signal_point = None

    if args.signal == 'land':
        signal_point = bsi_centroid
        source = bsi_source

    elif args.signal in ('coastal', 'teluk'):
        signal_point = snap_to_coastline(bsi_centroid[0], bsi_centroid[1])
        source = 'osm+bsi'
        if signal_point is None:
            print('  OSM coastline unavailable — using BSI centroid as fallback')
            signal_point = bsi_centroid
            source = bsi_source

    elif args.signal == 'river':
        signal_point = snap_to_river(bsi_centroid[0], bsi_centroid[1])
        source = 'osm+bsi'
        if signal_point is None:
            print('  OSM river unavailable — using BSI centroid as fallback')
            signal_point = bsi_centroid
            source = bsi_source

    label = args.label or f'{row.get("nama_kab","?")} {args.signal} zone'

    print(f'\n=== Result ===')
    print(f'  Incident:     {args.id}')
    print(f'  Signal point: {signal_point[0]}, {signal_point[1]}')
    print(f'  Signal type:  {args.signal}')
    print(f'  Lease:        {row["nama_usaha"]}')
    print(f'  Source:       {source}')

    # Write to incident_signals.json
    signals = {}
    if SIGNALS_JSON.exists():
        signals = json.loads(SIGNALS_JSON.read_text())

    signals[args.id] = {
        'signal_point': signal_point,
        'signal_type':  args.signal,
        'label':        label,
        'source':       source,
        'lease':        str(row['nama_usaha']),
        'bsi_centroid': bsi_centroid,
    }

    SIGNALS_JSON.write_text(json.dumps(signals, indent=2, ensure_ascii=False))
    print(f'\nWritten to {SIGNALS_JSON}')


if __name__ == '__main__':
    main()
