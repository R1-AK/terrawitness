"""
Extractor: uses Groq (free) to extract structured incident data from article text.

Free API key: https://console.groq.com  (no credit card required)
Add to pipeline/.env:  GROQ_API_KEY=gsk_...
"""

import json
import os
from groq import Groq

SYSTEM_PROMPT = """You are an expert analyst for TerraWitness, a civic satellite verification platform
monitoring ecological violations in Indonesia's critical mineral extraction zones.

Your job: analyze Indonesian news articles about environmental violations and extract
structured incident data in JSON format.

Be precise. If a field cannot be determined, use null.
Return only valid JSON — no markdown fences, no explanation, just the JSON object."""

EXTRACTION_PROMPT = """Analyze this news article and return a JSON object with exactly these fields:

{{
  "violation_type": "<one of: illegal_clearing | tailings_discharge | unauthorized_expansion | river_contamination | protected_area_breach>",
  "severity": "<one of: critical | high | medium | low>",
  "location": {{
    "desa": "<village/desa name or null>",
    "kecamatan": "<kecamatan name or null>",
    "kabupaten": "<kabupaten name or null>",
    "provinsi": "<province name or null>",
    "feature_name": "<named bay, river, island, or forest — or null>"
  }},
  "concession_holder": "<company name or null>",
  "post_text": "<most vivid resident quote OR most impactful harm description in Bahasa Indonesia, max 220 chars>",
  "impact_summary": "<1-2 sentences in English describing the environmental harm>",
  "area_ha": <affected area in hectares as number, or null>,
  "violation_flag": <true if clearly illegal or in protected zone>,
  "ndvi_before": <estimated NDVI before: healthy forest=0.75, degraded=0.55, agricultural=0.45>,
  "ndvi_after": <estimated NDVI after: bare/contaminated=0.10, disturbed=0.25, light damage=0.40>,
  "change_score": <float 0.0-1.0 reflecting severity of detectable land change>
}}

Severity guide:
- critical: national park / small island law violated, or severe contamination affecting human health
- high: legally restricted zone violated, or major ecosystem loss
- medium: unclear legal status, moderate impact
- low: minor or unconfirmed

Article:
---
TITLE: {title}
DATE: {date}
SOURCE: {source}

{text}
---"""


def extract_incident(article: dict) -> dict | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Get a free key at https://console.groq.com (no credit card needed)\n"
            "Then add to pipeline/.env:  GROQ_API_KEY=gsk_..."
        )

    client = Groq(api_key=api_key)

    prompt = EXTRACTION_PROMPT.format(
        title=article.get("title", ""),
        date=article.get("date", ""),
        source=article.get("source", ""),
        text=article.get("text", ""),
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model wraps in them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)

        # Attach article metadata
        data["source_url"]   = article["url"]
        data["source_name"]  = _prettify_source(article["source"])
        data["source_date"]  = article["date"][:10] if article.get("date") else ""
        data["post_date"]    = article.get("date", "")
        data["report_date"]  = article["date"][:10] if article.get("date") else ""
        data["status"]       = "verified"
        data["source_type"]  = _infer_source_type(article["source"])

        return data

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  [extractor] Parse error for {article['url']}: {e}")
        return None
    except Exception as e:
        print(f"  [extractor] Groq API error: {e}")
        return None


def _prettify_source(domain: str) -> str:
    return {
        "mongabay.co.id":  "Mongabay Indonesia",
        "betahita.id":     "Betahita",
        "tempo.co":        "Tempo",
        "kompas.com":      "Kompas",
        "kumparan.com":    "Kumparan",
        "detik.com":       "Detik",
        "forestdigest.com":"Forest Digest",
    }.get(domain, domain)


def _infer_source_type(domain: str) -> str:
    if domain in {"mongabay.co.id", "betahita.id", "forestdigest.com"}:
        return "investigation"
    return "local_news"
