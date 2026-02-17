---
name: tech-leaflet
description: Reference guide for Leaflet.js — interactive map with pan/zoom, layers, panes, and controls
user-invocable: false
---

# Leaflet.js

> Purpose: Interactive map with pan/zoom, layer controls, and custom pane ordering
> Docs: https://leafletjs.com/reference.html
> Version researched: 1.9.4 (CDN)

## Quick Start

```html
<!-- In <head> -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

<!-- Before </body> -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var map = L.map('map').setView([20, 0], 3);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
</script>
```

The map container `<div id="map">` must have an explicit height in CSS.

## Common Patterns

### Creating a map with an initial view

```javascript
var map = L.map('map', {
  center: [20, 0],
  zoom: 3,
  zoomControl: true
});
```

### Adding a tile layer

```javascript
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19
}).addTo(map);
```

For external tile servers (UNEP-WCMC, ArcGIS), use the same pattern with their URL template:

```javascript
var ecoregions = L.tileLayer(
  'https://data-gis.unep-wcmc.org/server/rest/services/Bio-geographicalRegions/Resolve_Ecoregions/MapServer/tile/{z}/{y}/{x}',
  { pane: 'contextPane', opacity: 0.6, attribution: 'UNEP-WCMC' }
);
```

Note: UNEP-WCMC uses `{z}/{y}/{x}` order (y before x), not the standard `{z}/{x}/{y}`.

### Custom panes for z-ordering

```javascript
// Create panes before adding layers
map.createPane('contextPane');
map.getPane('contextPane').style.zIndex = 400;

map.createPane('heatmapPane');
map.getPane('heatmapPane').style.zIndex = 450;

// Assign a layer to a pane via options
var layer = L.tileLayer(url, { pane: 'contextPane' });
```

Default pane z-index values: `tilePane` = 200, `overlayPane` = 400, `shadowPane` = 500, `markerPane` = 600, `tooltipPane` = 650, `popupPane` = 700. Custom panes with values between 400 and 700 sit between tile layers and markers.

### Layer toggle control

```javascript
var baseMaps = {
  "OpenStreetMap": osmLayer
};

var overlayMaps = {
  "WWF Ecoregions": ecoregions,
  "Key Biodiversity Areas": kbaLayer,
  "Human Footprint Index": hfiLayer,
  "Occurrence Heatmap": heatLayer
};

L.control.layers(baseMaps, overlayMaps).addTo(map);
```

Only layers listed in `overlayMaps` appear as checkboxes. The base map is a radio selection.

### Listening for map events

```javascript
map.on('zoomend', function () {
  console.log('zoom level:', map.getZoom());
});
```

## Gotchas & Pitfalls

- The map `<div>` must have a non-zero CSS height or the map renders as a blank 0-height element.
- `L.map('map')` must be called after the DOM element exists — put the `<script>` at the end of `<body>`, or wrap in a `DOMContentLoaded` listener.
- `setView` is required before the map will render tiles. Forgetting it results in a grey canvas.
- `L.control.layers` labels come from the object keys (strings), not from layer objects. Keep labels consistent with what you want shown in the UI.
- Tile URL templates are case-sensitive: UNEP-WCMC MapServer uses `{y}` and `{x}` (not `{Y}/{X}`), and the order is `{z}/{y}/{x}` (reverse of standard Leaflet).
- Custom pane z-indices only affect ordering within each CSS stacking context. The `tilePane` (200) will always appear below `overlayPane` (400) by default.

## Idiomatic Usage

Create all panes before adding any layers, at map initialisation:

```javascript
// Good — panes first, then layers
var map = L.map('map').setView([20, 0], 3);
map.createPane('contextPane');
map.getPane('contextPane').style.zIndex = 400;
map.createPane('heatmapPane');
map.getPane('heatmapPane').style.zIndex = 450;
// ... then add tile layers with pane option

// Avoid — adding layers before pane exists silently falls back to overlayPane
var layer = L.tileLayer(url, { pane: 'contextPane' });
layer.addTo(map);
map.createPane('contextPane'); // too late
```

Store layer references to manipulate them later (show/hide, update data):

```javascript
var heatLayer = L.heatLayer([], { radius: 20, pane: 'heatmapPane' }).addTo(map);
// Later:
heatLayer.setLatLngs(newPoints);
```
