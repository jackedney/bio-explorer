---
name: domain-species-occurrence-mapping
description: Domain knowledge — species occurrence mapping concepts for correct heatmap and contextual layer implementation
user-invocable: false
---

# Species Occurrence Mapping

> Relevance: Developers need to understand what occurrence data represents, how to interpret coordinate quality, and what the contextual layers (Ecoregions, KBAs, Human Footprint) mean in order to make correct implementation decisions — especially around data filtering, layer rendering order, and UI presentation.

## Core Concepts

### Species occurrence records

An **occurrence record** is a documented observation of a species at a specific place and time. GBIF aggregates these from:
- Natural history museum specimen collections (historical, precise location)
- Citizen science platforms like iNaturalist (recent, GPS-located)
- Research surveys (highly accurate, small sample)
- Regional biodiversity databases (variable quality)

Each record has coordinates (if georeferenced), a taxon name matched to the backbone taxonomy, and metadata about the observation event.

### Heatmap interpretation

A species occurrence heatmap visualises **observation density**, not necessarily true distribution:
- Dense clusters often reflect where observers are active, not where the species is most abundant
- Coastal cities, national parks, and roadsides are systematically over-represented
- Remote areas appear sparse even for wide-ranging species

This **sampling bias** is a known limitation of GBIF data. For a demo, this is acceptable — but the UI should not imply the heatmap shows "where the species lives" without qualification.

### WWF Ecoregions

Ecoregions are large areas of land defined by similar ecological characteristics — climate, vegetation, soil, and wildlife. The WWF Resolve Ecoregions classify the world into ~846 terrestrial ecoregions grouped into 14 biomes (tropical forests, tundra, deserts, etc.).

Use: Overlay with the occurrence heatmap to show which ecological zones a species inhabits. A mountain lion heatmap overlapping multiple ecoregions shows its ecological breadth.

### Key Biodiversity Areas (KBA) — and the WDPA proxy

**Key Biodiversity Areas** are sites contributing significantly to species conservation. They are identified through global criteria (range-restricted species, threatened species, congregations).

In this app, the KBA layer is backed by **WDPA (World Database of Protected Areas)** — legally protected areas (national parks, reserves, marine protected areas). WDPA has significant geographic overlap with KBAs but is not equivalent: protected areas are legally designated, KBAs are science-identified. The layer is labeled "Key Biodiversity Areas" per SPEC R5 as an acknowledged proxy.

### Human Footprint Index

The Human Footprint Index (HFI) quantifies human pressure on natural ecosystems, integrating data on:
- Population density
- Land transformation (agriculture, urbanisation)
- Infrastructure (roads, railways)
- Access (rivers, coast)

High HFI values (shown in warmer colours) indicate heavily human-modified landscapes. Overlaying with occurrence data shows whether a species tolerates human presence or is restricted to low-footprint areas.

## Mental Models

**Layers are independent data sources.** The three contextual layers (Ecoregions, KBA/WDPA, HFI) and the occurrence heatmap come from four completely different data pipelines. They happen to be co-displayed but have no direct relationship in the data model. The rendering order (heatmap on top) is a UI convention, not a data dependency.

**Occurrence data is a sample, not a census.** The 10,000-point cap is not a limitation of the species' range — it is a sample of the available records. The `total` field (full GBIF count) is meaningful context; `returned` is the rendered sample.

**Coordinate precision varies.** A record georeferenced at country level will plot at the country centroid. Such points create artificial hotspots at political capitals and country centroids (e.g. 0°N, 0°E for records defaulting to the prime meridian/equator intersection in the Gulf of Guinea). Filtering `hasGeospatialIssue=false` removes the worst offenders.

## Edge Cases and Gotchas

- **The Gulf of Guinea cluster**: Many records with unknown coordinates default to (0, 0). Filter `hasGeospatialIssue=false` to exclude these.
- **Domestic species**: Common species (house sparrow, dandelion) have millions of records concentrated in densely populated regions. The 10,000 sample will look very urban-biased.
- **Marine species on land**: Some historical records place marine species at coastal town coordinates (nearest port). These appear as onshore points in the heatmap.
- **Subspecies and synonyms**: GBIF may return separate occurrence sets for a species' synonyms. The `/species/match` endpoint resolves to the accepted taxon key, which aggregates records from synonyms.
- **Layer opacity matters**: Ecoregion tiles are brightly coloured. At full opacity they obscure the heatmap. The DESIGN.md specifies `opacity: 0.6` for contextual tile layers — this is a UX decision to keep the heatmap readable.
- **Tile server availability**: UNEP-WCMC and ArcGIS Online tiles are third-party hosted. If they are unavailable, the contextual layers will be blank, but the app itself continues to function.

## Validation Rules

For a correct implementation:

1. The heatmap must render visually above all contextual layers at all zoom levels
2. Each contextual layer checkbox independently shows/hides that layer without affecting others
3. Points at (0, 0) or obviously erroneous coordinates should not appear (achieved via `hasGeospatialIssue=false` filter)
4. The occurrence count displayed to the user should show the GBIF total, not just the sampled count
5. Searching for a new species replaces the previous heatmap — no accumulation

Test invariants:
```
- heatmap z-index (450) > contextPane z-index (400)
- turning off WWF Ecoregions does not affect KBA or HFI visibility
- after two consecutive searches, only the second species' points are visible
```
