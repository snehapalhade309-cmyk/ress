/**
 * RESQAI - Tactical Leaflet Map Controller
 * Real Leaflet Map with Incidents, Resources, Shelters & Routing Overlays
 */

let resqaiMap = null;
let incidentLayer = null;
let resourceLayer = null;
let shelterLayer = null;
let routeLayer = null;
let tempClickMarker = null;

document.addEventListener('DOMContentLoaded', () => {
  initLeafletMap();
  initMapControls();
});

/**
 * Initialize Leaflet Map Instance
 */
function initLeafletMap() {
  const mapContainer = document.getElementById('leaflet-map');
  if (!mapContainer) return;

  // Center around Pune Disaster Operations Cluster
  resqaiMap = L.map('leaflet-map', {
    center: [18.5350, 73.8480],
    zoom: 12,
    zoomControl: true,
    attributionControl: true
  });
  window.resqaiMap = resqaiMap;

  // OpenStreetMap Tile Layer (with dark tactical filter CSS)
  const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors | ResQAI Decision Net',
    className: 'tactical-tiles'
  }).addTo(resqaiMap);

  // Initialize Layer Groups
  incidentLayer = L.layerGroup().addTo(resqaiMap);
  resourceLayer = L.layerGroup().addTo(resqaiMap);
  shelterLayer = L.layerGroup().addTo(resqaiMap);
  routeLayer = L.layerGroup().addTo(resqaiMap);

  // Click on map to pick coordinates for Report Emergency form
  resqaiMap.on('click', (e) => {
    const lat = e.latlng.lat.toFixed(5);
    const lon = e.latlng.lng.toFixed(5);
    
    // Update Report Form inputs
    const latInput = document.getElementById('rep-lat');
    const lonInput = document.getElementById('rep-lon');
    if (latInput && lonInput) {
      latInput.value = lat;
      lonInput.value = lon;
    }

    // Place temporary marker
    if (tempClickMarker) resqaiMap.removeLayer(tempClickMarker);
    tempClickMarker = L.circleMarker([lat, lon], {
      radius: 7,
      color: '#00e5ff',
      fillColor: '#00e5ff',
      fillOpacity: 0.8
    }).addTo(resqaiMap);

    tempClickMarker.bindPopup(`<b>Selected Coordinates</b><br>${lat}, ${lon}<br><small>Transferred to Report Form</small>`).openPopup();
    showToast(`Coordinates set to ${lat}, ${lon}`, 'info');

    // Trigger risk preview update if on report tab
    if (typeof triggerRiskPreview === 'function') {
      triggerRiskPreview();
    }
  });
}

/**
 * Custom SVG DivIcon Generators
 */
function createIncidentMarkerIcon(category, type) {
  const cat = (category || 'medium').toLowerCase();
  let pinClass = `custom-marker-pin marker-${cat}`;

  let iconSvg = '';
  if (type === 'flood') {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>';
  } else if (type === 'fire') {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>';
  } else if (type === 'landslide') {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m8 3 4 8 5-5 5 15H2L8 3z"/></svg>';
  } else {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
  }

  return L.divIcon({
    className: 'custom-div-marker',
    html: `<div class="${pinClass}">${iconSvg}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17]
  });
}

function createResourceMarkerIcon(status, type) {
  const isDisp = status === 'dispatched';
  const pinClass = `custom-marker-pin marker-resource ${isDisp ? 'dispatched' : ''}`;
  
  let iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="16" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/></svg>';
  if (type === 'ambulance') {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v8"/><path d="M8 12h8"/><rect width="18" height="14" x="3" y="5" rx="2"/></svg>';
  } else if (type === 'rescue_boat') {
    iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>';
  }

  return L.divIcon({
    className: 'custom-div-marker',
    html: `<div class="${pinClass}">${iconSvg}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });
}

function createShelterMarkerIcon() {
  return L.divIcon({
    className: 'custom-div-marker',
    html: `<div class="custom-marker-pin marker-shelter"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });
}

/**
 * Render Markers on Map from Datasets
 */
function renderMapMarkers() {
  if (!resqaiMap) return;

  // 1. Incidents
  incidentLayer.clearLayers();
  AppState.incidents.forEach(inc => {
    if (inc.latitude && inc.longitude) {
      const marker = L.marker([inc.latitude, inc.longitude], {
        icon: createIncidentMarkerIcon(inc.risk_category, inc.type)
      });

      const popupContent = `
        <div style="min-width: 200px;">
          <div class="popup-title">${inc.incident_code}: ${inc.title}</div>
          <div class="popup-meta">
            <strong>Type:</strong> ${inc.type.toUpperCase()}<br>
            <strong>Risk Score:</strong> <span style="color:var(--sev-${inc.risk_category.toLowerCase()}); font-weight:700;">${inc.calculated_risk_score}/100 (${inc.risk_category})</span><br>
            <strong>Location:</strong> ${inc.location_name}<br>
            <strong>Status:</strong> ${inc.status.toUpperCase()}
          </div>
          <button class="popup-btn" onclick="showIncidentDetail(${inc.id})">Inspect Incident & Dispatch</button>
        </div>
      `;

      marker.bindPopup(popupContent);
      incidentLayer.addLayer(marker);
    }
  });

  // 2. Resources (Simulated Fleet)
  resourceLayer.clearLayers();
  AppState.resources.forEach(res => {
    if (res.latitude && res.longitude) {
      const marker = L.marker([res.latitude, res.longitude], {
        icon: createResourceMarkerIcon(res.status, res.type)
      });

      const popupContent = `
        <div>
          <div class="popup-title">${res.name}</div>
          <div class="popup-meta">
            <strong>Code:</strong> ${res.resource_code}<br>
            <strong>Type:</strong> ${res.type.replace('_', ' ').toUpperCase()}<br>
            <strong>Status:</strong> <span style="font-weight:700; color:${res.status === 'available' ? 'var(--sev-low)' : 'var(--sev-high)'}">${res.status.toUpperCase()}</span><br>
            <strong>Base:</strong> ${res.base_station}
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      resourceLayer.addLayer(marker);
    }
  });

  // 3. Shelters
  shelterLayer.clearLayers();
  AppState.shelters.forEach(shl => {
    if (shl.latitude && shl.longitude) {
      const marker = L.marker([shl.latitude, shl.longitude], {
        icon: createShelterMarkerIcon()
      });

      const occPct = shl.occupancy_pct || 0;
      const popupContent = `
        <div>
          <div class="popup-title">${shl.name}</div>
          <div class="popup-meta">
            <strong>Capacity:</strong> ${shl.current_occupancy} / ${shl.total_capacity} (${occPct}% full)<br>
            <strong>Address:</strong> ${shl.address}<br>
            <strong>Verification:</strong> <span style="color:var(--sev-low); font-weight:700;">VERIFIED HIGH-GROUND</span>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      shelterLayer.addLayer(marker);
    }
  });
}

/**
 * Draw Evacuation Route Polyline
 */
function drawRouteOnMap(geoJsonGeometry, origin, dest, summary) {
  if (!resqaiMap || !routeLayer) return;

  routeLayer.clearLayers();

  if (geoJsonGeometry && geoJsonGeometry.coordinates) {
    // GeoJSON is [lon, lat], Leaflet polyline expects [lat, lon]
    const latLngs = geoJsonGeometry.coordinates.map(coord => [coord[1], coord[0]]);

    const polyline = L.polyline(latLngs, {
      color: '#00e5ff',
      weight: 5,
      opacity: 0.95,
      dashArray: summary.fallback ? '8, 8' : null
    }).addTo(routeLayer);

    resqaiMap.fitBounds(polyline.getBounds(), { padding: [50, 50] });

    polyline.bindPopup(`
      <b>Advisory Evacuation Route</b><br>
      Distance: ${summary.distance_km} km<br>
      Est. Transit: ${summary.duration_minutes} mins<br>
      <small style="color:var(--sev-high);">${summary.safety_disclaimer}</small>
    `).openPopup();
  }
}

/**
 * Map Overlays Controls (Search, Locate, Layer Checkboxes)
 */
function initMapControls() {
  // Layer Toggles
  document.getElementById('layer-incidents').addEventListener('change', (e) => {
    if (e.target.checked) resqaiMap.addLayer(incidentLayer);
    else resqaiMap.removeLayer(incidentLayer);
  });

  document.getElementById('layer-resources').addEventListener('change', (e) => {
    if (e.target.checked) resqaiMap.addLayer(resourceLayer);
    else resqaiMap.removeLayer(resourceLayer);
  });

  document.getElementById('layer-shelters').addEventListener('change', (e) => {
    if (e.target.checked) resqaiMap.addLayer(shelterLayer);
    else resqaiMap.removeLayer(shelterLayer);
  });

  // Geocode Search Input
  const searchInput = document.getElementById('map-search-input');
  let searchTimer = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    const query = e.target.value.trim();
    if (query.length < 3) return;

    searchTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
        if (res.ok) {
          const results = await res.json();
          if (results.length > 0) {
            const first = results[0];
            resqaiMap.flyTo([first.lat, first.lon], 14, { duration: 1.5 });
            showToast(`Map centered to ${first.display_name.split(',')[0]}`, 'info');
          }
        }
      } catch (err) {
        console.warn('Geocoding error:', err);
      }
    }, 600);
  });

  // Browser Geolocation
  document.getElementById('btn-map-locate').addEventListener('click', () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          resqaiMap.flyTo([lat, lon], 14);
          L.circleMarker([lat, lon], { radius: 8, color: '#00e5ff', fillColor: '#00e5ff' })
            .addTo(resqaiMap)
            .bindPopup('<b>Current Dispatcher GPS Fix</b>')
            .openPopup();
          showToast('GPS fix acquired and focused.', 'info');
        },
        (err) => {
          showToast('Geolocation permission denied or timed out.', 'warning');
        },
        { timeout: 8000 }
      );
    } else {
      showToast('Browser does not support geolocation.', 'warning');
    }
  });

  // Pick coords button inside report form
  const btnPickCoords = document.getElementById('btn-pick-coords');
  if (btnPickCoords) {
    btnPickCoords.addEventListener('click', () => {
      if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            document.getElementById('rep-lat').value = pos.coords.latitude.toFixed(5);
            document.getElementById('rep-lon').value = pos.coords.longitude.toFixed(5);
            showToast('GPS coordinates autofilled into report form.', 'info');
            if (typeof triggerRiskPreview === 'function') triggerRiskPreview();
          },
          (err) => {
            showToast('Could not acquire GPS fix. Please click on the Live Map instead.', 'warning');
          }
        );
      }
    });
  }
}
