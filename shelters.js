/**
 * RESQAI - Shelters & Evacuation Routing Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const btnCalc = document.getElementById('btn-calc-route');
  if (btnCalc) {
    btnCalc.addEventListener('click', calculateEvacuationRoute);
  }
});

/**
 * Fetch and Render Shelters
 */
async function loadShelters() {
  try {
    const res = await fetch('/api/shelters');
    if (!res.ok) throw new Error('Shelter fetch failed');
    const shelters = await res.json();
    AppState.shelters = shelters;

    renderSheltersTable(shelters);
    populateRouteDropdowns();

    if (typeof renderMapMarkers === 'function') {
      renderMapMarkers();
    }
  } catch (err) {
    console.error('Error loading shelters:', err);
  }
}

/**
 * Render Shelters Table
 */
function renderSheltersTable(shelters) {
  const tbody = document.getElementById('shelters-table-body');
  if (!tbody) return;

  if (shelters.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-dim); padding:2rem;">No shelters registered.</td></tr>';
    return;
  }

  tbody.innerHTML = shelters.map(s => {
    const occPct = s.occupancy_pct || 0;
    const isFull = occPct >= 90;
    const progressColor = isFull ? 'var(--sev-critical)' : (occPct >= 70 ? 'var(--sev-high)' : 'var(--sev-low)');

    const amenities = Array.isArray(s.amenities) ? s.amenities : [];
    const amHtml = amenities.map(a => `
      <span class="badge" style="background:var(--bg-surface); color:var(--text-muted); font-size:0.65rem; border:1px solid var(--border-subtle); margin-right:3px;">
        ${a.replace('_', ' ')}
      </span>
    `).join('');

    return `
      <tr>
        <td><strong style="color:var(--accent-cyan); font-family:var(--font-mono);">${s.shelter_code}</strong></td>
        <td>
          <div style="font-weight:700; color:#fff;">${s.name}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${s.address}</div>
        </td>
        <td><span class="badge badge-info">${s.type.replace('_', ' ').toUpperCase()}</span></td>
        <td><strong>${s.total_capacity}</strong></td>
        <td>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <div style="flex:1; width:80px; height:6px; background:#1e293b; border-radius:var(--radius-full); overflow:hidden;">
              <div style="width:${occPct}%; height:100%; background:${progressColor};"></div>
            </div>
            <span style="font-size:0.75rem; font-family:var(--font-mono);">${occPct}%</span>
          </div>
          <div style="font-size:0.7rem; color:var(--text-dim); margin-top:2px;">${s.available_spaces} spaces left</div>
        </td>
        <td>${amHtml}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="selectShelterForRoute(${s.id})">
            Plan Evacuation
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Populate Route Planner Dropdowns
 */
function populateRouteDropdowns() {
  const incSelect = document.getElementById('route-src-incident');
  const shlSelect = document.getElementById('route-dest-shelter');
  if (!incSelect || !shlSelect) return;

  incSelect.innerHTML = (AppState.incidents || []).map(inc => `
    <option value="${inc.id}" data-lat="${inc.latitude}" data-lon="${inc.longitude}">
      ${inc.incident_code}: ${inc.title}
    </option>
  `).join('');

  shlSelect.innerHTML = (AppState.shelters || []).map(shl => `
    <option value="${shl.id}" data-lat="${shl.latitude}" data-lon="${shl.longitude}">
      ${shl.shelter_code}: ${shl.name} (${shl.available_spaces} spaces available)
    </option>
  `).join('');
}

function selectShelterForRoute(shelterId) {
  const shlSelect = document.getElementById('route-dest-shelter');
  if (shlSelect) {
    shlSelect.value = shelterId;
    calculateEvacuationRoute();
  }
}

/**
 * Compute Evacuation Route
 */
async function calculateEvacuationRoute() {
  const incSelect = document.getElementById('route-src-incident');
  const shlSelect = document.getElementById('route-dest-shelter');
  if (!incSelect || !shlSelect) return;

  const incOpt = incSelect.options[incSelect.selectedIndex];
  const shlOpt = shlSelect.options[shlSelect.selectedIndex];

  if (!incOpt || !shlOpt) {
    showToast('Please select both an incident and shelter target.', 'warning');
    return;
  }

  const oLat = incOpt.getAttribute('data-lat');
  const oLon = incOpt.getAttribute('data-lon');
  const dLat = shlOpt.getAttribute('data-lat');
  const dLon = shlOpt.getAttribute('data-lon');

  if (!oLat || !oLon || !dLat || !dLon || oLat === 'null') {
    showToast('Selected incident does not have GPS coordinates.', 'warning');
    return;
  }

  try {
    const url = `/api/routes/evacuation?origin_lat=${oLat}&origin_lon=${oLon}&dest_lat=${dLat}&dest_lon=${dLon}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Routing computation failed');

    const data = await res.json();

    // Display summary in card
    const resBox = document.getElementById('route-calc-result');
    document.getElementById('route-dist-val').textContent = `${data.distance_km} km`;
    document.getElementById('route-dur-val').textContent = `${data.duration_minutes} mins`;
    resBox.style.display = 'block';

    // Draw route on map & switch to map
    if (typeof drawRouteOnMap === 'function') {
      drawRouteOnMap(data.geometry, data.origin, data.destination, data);
      showToast(`Evacuation route mapped (${data.distance_km} km). Switching to Live Map.`, 'info');
      switchTab('tab-map');
    }
  } catch (err) {
    showToast('Failed to calculate evacuation routing.', 'error');
  }
}
