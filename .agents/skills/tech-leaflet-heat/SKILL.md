---
name: tech-leaflet-heat
description: Reference guide for Leaflet.heat — client-side heatmap rendering from point data
user-invocable: false
---

# Leaflet.heat

> Purpose: Client-side heatmap rendering from species occurrence point data
> Docs: https://github.com/Leaflet/Leaflet.heat
> Version researched: 0.2.0 (CDN)

## Quick Start

Leaflet.heat must be loaded **after** Leaflet:

```html
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
```

Create and add a heat layer:

```javascript
var heat = L.heatLayer([], { radius: 20 }).addTo(map);
// Load data later:
heat.setLatLngs([[51.5, -0.1], [48.8, 2.3]]);
```

## Common Patterns

### Initialisation with options

```javascript
var heat = L.heatLayer([], {
  radius: 20,
  blur: 15,
  maxZoom: 17,
  max: 1.0,
  minOpacity: 0.05,
  gradient: { 0.4: 'blue', 0.65: 'lime', 1: 'red' },
  pane: 'heatmapPane'   // assign to custom pane for z-ordering
}).addTo(map);
```

### Data format

Each point is either a two-element array `[lat, lng]` or three-element `[lat, lng, intensity]`:

```javascript
// Without intensity (all points equal weight)
var points = [[51.5, -0.1], [48.8, 2.3], [40.7, -74.0]];

// With intensity (0.0–1.0, relative to max option)
var points = [[51.5, -0.1, 0.8], [48.8, 2.3, 0.3]];
```

The backend `/api/occurrences` returns `[[lat, lng], ...]` — no intensity column needed for a uniform heatmap.

### Replacing all data after a search

```javascript
fetch(`/api/occurrences?taxon_key=${taxonKey}`)
  .then(r => r.json())
  .then(data => {
    heat.setLatLngs(data.points);   // replaces existing data and redraws
  });
```

### Adding individual points incrementally

```javascript
heat.addLatLng([lat, lng]);         // adds one point and redraws
heat.addLatLng([lat, lng, 0.5]);    // with intensity
```

### Updating options after creation

```javascript
heat.setOptions({ radius: 30, gradient: { 0.5: 'yellow', 1: 'red' } });
```

### Assigning to a custom pane (for render-above-context-layers requirement)

```javascript
map.createPane('heatmapPane');
map.getPane('heatmapPane').style.zIndex = 450;

var heat = L.heatLayer([], {
  radius: 20,
  pane: 'heatmapPane'
}).addTo(map);
```

Pane z-index 450 places the heatmap above `contextPane` (400) and below Leaflet's default `markerPane` (600).

## Gotchas & Pitfalls

- Leaflet.heat must be loaded after the main Leaflet script — it extends `L` at load time and will throw if `L` is not defined.
- `setLatLngs([])` clears the heatmap. Useful for resetting when the user searches for a new species.
- Performance degrades noticeably above ~10,000 points. The backend should sample down to this limit before returning data.
- The `gradient` option takes stop positions as keys (numbers 0.0–1.0 as strings or numbers) and CSS colour strings as values. Malformed gradient objects silently use the default blue-lime-red scale.
- `max` is the maximum intensity value in your dataset, used for normalisation. If your data uses raw occurrence counts rather than normalised 0–1 values, set `max` to the actual maximum count.
- The `pane` option must name a pane that exists **before** the heat layer is created. Adding a layer to a non-existent pane silently falls back to `overlayPane`.
- `redraw()` is rarely needed — `setLatLngs`, `addLatLng`, and `setOptions` all trigger a redraw automatically.

## Idiomatic Usage

Clear and refill on each new search — do not accumulate across searches:

```javascript
// Good — replace data atomically
function showHeatmap(points) {
  heat.setLatLngs(points);
}

// Avoid — accumulates from previous searches
function showHeatmap(points) {
  points.forEach(p => heat.addLatLng(p));
}
```

Use `setLatLngs` for batch updates (single redraw); use `addLatLng` only for streaming/live scenarios where you add one point at a time.

Set the `pane` option at construction time; you cannot change the pane of an existing layer:

```javascript
// Good — pane set at construction
var heat = L.heatLayer([], { pane: 'heatmapPane' }).addTo(map);

// Avoid — no supported API to change pane after creation
heat.options.pane = 'heatmapPane';  // does not work
```
