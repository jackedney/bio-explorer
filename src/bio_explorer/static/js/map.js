/* global L */

// Map initialisation
var map = L.map("map").setView([20, 0], 3);

// Create custom panes before adding any layers
map.createPane("contextPane");
map.getPane("contextPane").style.zIndex = 400;

map.createPane("heatmapPane");
map.getPane("heatmapPane").style.zIndex = 450;

// Base layer
var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
}).addTo(map);

// Contextual tile layers (assigned to contextPane, opacity 0.6)
var ecoregions = L.tileLayer(
    "https://data-gis.unep-wcmc.org/server/rest/services/Bio-geographicalRegions/Resolve_Ecoregions/MapServer/tile/{z}/{y}/{x}",
    { pane: "contextPane", opacity: 0.6, attribution: "UNEP-WCMC" },
);

var kba = L.tileLayer(
    "https://data-gis.unep-wcmc.org/server/rest/services/ProtectedSites/The_World_Database_of_Protected_Areas/MapServer/tile/{z}/{y}/{x}",
    { pane: "contextPane", opacity: 0.6, attribution: "UNEP-WCMC" },
);

var hfi = L.tileLayer(
    "https://tiles.arcgis.com/tiles/RTK5Unh1Z71JKIiR/arcgis/rest/services/HumanFootprint/MapServer/tile/{z}/{y}/{x}",
    { pane: "contextPane", opacity: 0.6, attribution: "ArcGIS Online" },
);

// Heatmap layer (starts empty, assigned to heatmapPane)
var heat = L.heatLayer([], {
    radius: 20,
    blur: 15,
    maxZoom: 17,
    pane: "heatmapPane",
}).addTo(map);

// Layer toggle control
var baseMaps = {
    OpenStreetMap: osm,
};

var overlayMaps = {
    "WWF Ecoregions": ecoregions,
    "Key Biodiversity Areas": kba,
    "Human Footprint Index": hfi,
    "Occurrence Heatmap": heat,
};

L.control.layers(baseMaps, overlayMaps).addTo(map);

// Error display helpers
function showError(message) {
    var el = document.getElementById("error-message");
    el.textContent = message;
    el.style.display = "block";
}

function clearError() {
    var el = document.getElementById("error-message");
    el.textContent = "";
    el.style.display = "none";
}

// Search handler
async function handleSearch(query) {
    clearError();
    heat.setLatLngs([]);

    var res = await fetch(
        "/api/species/search?q=" + encodeURIComponent(query),
    );
    if (!res.ok) {
        var errData = await res.json();
        showError(errData.error || "Search failed");
        return;
    }

    var searchData = await res.json();
    if (!searchData.results || searchData.results.length === 0) {
        showError("No species found for: " + query);
        return;
    }

    var taxonKey = searchData.results[0].key;

    var occRes = await fetch("/api/occurrences?taxon_key=" + taxonKey);
    if (!occRes.ok) {
        var occErr = await occRes.json();
        showError(occErr.error || "Failed to load occurrences");
        return;
    }

    var occData = await occRes.json();
    heat.setLatLngs(occData.points);
}

// Wire up form submission
document.getElementById("search-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = document.getElementById("search-input");
    var query = input.value.trim();
    if (query) {
        handleSearch(query);
    }
});
