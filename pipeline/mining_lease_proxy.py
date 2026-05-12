"""
Rank mining lease polygons as location proxies for weak public text signals.

This parser intentionally avoids heavy GIS dependencies so it can run in the
current lightweight competition environment. It reads the WIUP_2025 shapefile
and DBF directly, then scores candidate leases from text clues.

Usage:
  python mining_lease_proxy.py --text "Raja Ampat bukan untuk ditambang" --commodity NIKEL
  python mining_lease_proxy.py --text "Teluk Buli Halmahera Timur nikel" --top 10
"""

import argparse
import json
import re
import struct
from pathlib import Path


DEFAULT_BASE = Path(r"D:\2026\Competition\Indonesia Mining Lease\WIUP_2025")


def normalize(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "").upper()).strip()


def read_dbf(path: Path) -> list[dict]:
    with path.open("rb") as f:
        header = f.read(32)
        record_count = struct.unpack("<I", header[4:8])[0]
        header_len = struct.unpack("<H", header[8:10])[0]
        record_len = struct.unpack("<H", header[10:12])[0]

        fields = []
        offset = 1
        while True:
            desc = f.read(32)
            if not desc or desc[0] == 0x0D:
                break
            name = desc[0:11].split(b"\x00", 1)[0].decode("utf-8", "replace")
            field_type = chr(desc[11])
            field_len = desc[16]
            decimals = desc[17]
            fields.append((name, field_type, field_len, decimals, offset))
            offset += field_len

        f.seek(header_len)
        rows = []
        for idx in range(record_count):
            record = f.read(record_len)
            if not record or record[0:1] == b"*":
                continue
            row = {"_idx": idx}
            for name, field_type, field_len, decimals, offset in fields:
                raw = record[offset:offset + field_len]
                value = raw.decode("utf-8", "replace").strip()
                if field_type in "NF" and value:
                    try:
                        value = float(value) if decimals else int(float(value))
                    except ValueError:
                        pass
                row[name] = value
            rows.append(row)
        return rows


def read_shape_summaries(path: Path) -> list[dict]:
    summaries = []
    with path.open("rb") as f:
        f.seek(100)
        while True:
            header = f.read(8)
            if len(header) < 8:
                break
            _, words = struct.unpack(">2i", header)
            content = f.read(words * 2)
            if len(content) < 44:
                summaries.append({})
                continue

            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type != 5:
                summaries.append({"shape_type": shape_type})
                continue

            minx, miny, maxx, maxy = struct.unpack("<4d", content[4:36])
            parts_count, point_count = struct.unpack("<2i", content[36:44])
            summaries.append({
                "shape_type": shape_type,
                "bbox": [minx, miny, maxx, maxy],
                "centroid": [(minx + maxx) / 2, (miny + maxy) / 2],
                "parts": parts_count,
                "points": point_count,
            })
    return summaries


def load_leases(base: Path = DEFAULT_BASE) -> list[dict]:
    rows = read_dbf(base.with_suffix(".dbf"))
    shapes = read_shape_summaries(base.with_suffix(".shp"))
    if len(rows) != len(shapes):
        raise RuntimeError(f"DBF/SHP count mismatch: {len(rows)} rows, {len(shapes)} shapes")
    for row, shape in zip(rows, shapes):
        row.update(shape)
    return rows


def score_lease(row: dict, text: str, commodity_hint: str | None) -> tuple[float, list[str]]:
    text_norm = normalize(text)
    commodity = normalize(row.get("komoditas"))
    province = normalize(row.get("nama_prov"))
    district = normalize(row.get("nama_kab"))
    company = normalize(row.get("nama_usaha"))
    location = normalize(row.get("lokasi"))
    activity = normalize(row.get("kegiatan"))

    score = 0.0
    reasons = []

    if commodity_hint and normalize(commodity_hint) in commodity:
        score += 0.20
        reasons.append(f"commodity={commodity}")
    elif "NIKEL" in text_norm and "NIKEL" in commodity:
        score += 0.20
        reasons.append("text and lease both indicate nickel")

    for label, value, weight in [
        ("province", province, 0.10),
        ("district", district, 0.25),
        ("company", company, 0.20),
        ("location", location, 0.15),
    ]:
        if value and value in text_norm:
            score += weight
            reasons.append(f"{label} match: {value}")

    # Token overlap catches cases like "Gag", "Buli", "Weda", or "Kabaena".
    tokens = {t for t in re.split(r"[^A-Z0-9]+", text_norm) if len(t) >= 4}
    lease_tokens = {
        t for t in re.split(r"[^A-Z0-9]+", f"{company} {location} {district}")
        if len(t) >= 4
    }
    overlap = sorted(tokens & lease_tokens)
    if overlap:
        token_score = min(0.20, 0.05 * len(overlap))
        score += token_score
        reasons.append("token overlap: " + ", ".join(overlap[:5]))

    if "OPERASI PRODUKSI" in activity:
        score += 0.05
        reasons.append("production lease")

    return score, reasons


def rank_leases(text: str, commodity_hint: str | None, top: int) -> list[dict]:
    ranked = []
    for row in load_leases():
        score, reasons = score_lease(row, text, commodity_hint)
        if score <= 0:
            continue
        ranked.append({
            "score": round(score, 3),
            "reasons": reasons,
            "centroid_lonlat": row.get("centroid"),
            "bbox": row.get("bbox"),
            "objectid": row.get("objectid"),
            "province": row.get("nama_prov"),
            "district": row.get("nama_kab"),
            "company": row.get("nama_usaha"),
            "commodity": row.get("komoditas"),
            "activity": row.get("kegiatan"),
            "license_type": row.get("jenis_izin"),
            "area_ha": row.get("luas_sk"),
            "location_text": row.get("lokasi"),
            "kode_wiup": row.get("kode_wiup"),
        })
    return sorted(ranked, key=lambda x: x["score"], reverse=True)[:top]


def main():
    parser = argparse.ArgumentParser(description="Rank WIUP mining leases for a weak text signal.")
    parser.add_argument("--text", required=True, help="Public post/news text to locate.")
    parser.add_argument("--commodity", default=None, help="Optional commodity hint, e.g. NIKEL.")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    print(json.dumps(rank_leases(args.text, args.commodity, args.top), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
