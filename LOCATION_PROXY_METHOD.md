# TerraWitness Location Proxy Method

TerraWitness does not treat an administrative place name as the final location.
It converts a weak public signal, such as "Raja Ampat" in a post, into a ranked
set of geospatial candidates with an uncertainty radius.

## Core Idea

Most public environmental reports contain partial geography: a district, island,
river, bay, village, company, or ecosystem. Existing conflict maps often stop at
that administrative label. TerraWitness narrows the location by combining those
text clues with domain-specific spatial layers.

## Candidate Generation

For each report, generate candidate locations from:

- Named places in text: villages, islands, bays, rivers, concessions.
- Administrative hierarchy: province, district, subdistrict, village polygons.
- Mining context: known nickel concessions, operators, ports, haul roads,
  smelter corridors, and industrial parks.
- Environmental context: rivers, coastlines, mangroves, reefs, forest zones,
  protected areas, and small-island zones.
- Remote-sensing context: recent vegetation, turbidity, or bare-earth anomaly
  hotspots near the reported area.

## Scoring

Each candidate receives a score:

```text
score(c) =
  0.25 * toponym_match(c)
+ 0.20 * admin_containment(c)
+ 0.20 * operator_or_concession_match(c)
+ 0.15 * ecosystem_match(c)
+ 0.15 * satellite_anomaly_match(c)
+ 0.05 * source_specificity(c)
```

The weights are deliberately transparent for the MVP. They can later be learned
from validated historical cases.

When mining lease polygons are available, TerraWitness uses them before falling
back to an administrative centroid. A social post that says only "Raja Ampat"
and "nikel" can therefore be narrowed to the highest-scoring lease polygon,
instead of being placed at the centre of Raja Ampat district.

## Proxy Output

TerraWitness outputs:

- Proxy coordinate: the highest-scoring candidate, or a probability-weighted
  centroid if several candidates remain plausible.
- Confidence class: exact, feature, village, subdistrict, district, or regional.
- Uncertainty radius: a distance buffer derived from candidate spread and
  administrative precision.
- Evidence trail: the text and spatial layers that justified the proxy.

## Example

Input text:

```text
Raja Ampat bukan untuk ditambang...
```

Naive result:

```text
Raja Ampat district centroid
```

TerraWitness result:

```text
GAG NIKEL lease proxy, because the text mentions Raja Ampat + nickel mining,
and WIUP_2025 contains a GAG NIKEL production polygon in that seascape.
```

This is the novelty: TerraWitness moves from "where is the administrative area?"
to "where is the most plausible environmental harm location, and how uncertain
are we?"

## Mining Extent Detection Inside A Lease

The lease polygon is not the same as the active mining footprint. After the
candidate lease is selected, TerraWitness can detect likely active mining cells
inside that polygon using Sentinel-2 indices:

```text
NDVI = (NIR - Red) / (NIR + Red)
NDBI = (SWIR - NIR) / (SWIR + NIR)
Bare or built-up mining candidate =
  NDVI < 0.30
  AND NDBI > 0.05
  AND slope mask / water mask passes
  AND persistent across at least 2 cloud-free dates
```

For nickel laterite mining, the useful signal is often a combination of low
vegetation, exposed red/brown soil, haul-road geometry, and expansion over time.
The MVP should show this as "candidate active footprint" until validated against
high-resolution imagery or field evidence.
