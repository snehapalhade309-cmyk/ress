/**
 * RESQAI - Smart Dispatch & Fleet Management Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const filterSelect = document.getElementById('filter-fleet-status');
  if (filterSelect) {
    filterSelect.addEventListener('change', () => {
      renderFleetTable(AppState.resources, filterSelect.value);
    });
  }
});

/**
 * Fetch and Render Fleet Resources
 */
async function loadResources() {
  try {
    const res = await fetch('/api/resources');
    if (!res.ok) throw new Error('Fleet fetch failed');
    const resources = await res.json();
    AppState.resources = resources;

    const filter = document.getElementById('filter-fleet-status')?.value || 'all';
    renderFleetTable(resources, filter);
    renderQuickFleetList(resources);

    if (typeof renderMapMarkers === 'function') {
      renderMapMarkers();
    }
  } catch (err) {
    console.error('Fleet loading error:', err);
  }
}

/**
 * Render Smart Dispatch Tab Fleet Matrix
 */
function renderFleetTable(resources, filterStatus = 'all') {
  const tbody = document.getElementById('fleet-table-body');
  if (!tbody) return;

  let filtered = resources;
  if (filterStatus !== 'all') {
    filtered = resources.filter(r => r.status === filterStatus);
  }

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-dim); padding:2rem;">No units matching current filter.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(r => {
    const isAvail = r.status === 'available';
    const statusBadge = isAvail
      ? '<span class="badge badge-available">AVAILABLE</span>'
      : '<span class="badge badge-dispatched">DISPATCHED</span>';

    const caps = Array.isArray(r.capabilities) ? r.capabilities : [];
    const capsHtml = caps.map(c => `
      <span class="badge" style="background:var(--bg-surface); color:var(--text-muted); font-size:0.65rem; border:1px solid var(--border-subtle); margin-right:3px;">
        ${c.replace('_', ' ')}
      </span>
    `).join('');

    const assignedHtml = r.assigned_incident_id
      ? `<strong style="color:var(--sev-high); font-family:var(--font-mono);">INC #${r.assigned_incident_id}</strong>`
      : '<span style="color:var(--text-dim); font-size:0.75rem;">None (Standby)</span>';

    const actionBtn = isAvail
      ? `<button class="btn btn-secondary btn-sm" onclick="switchTab('tab-overview'); showToast('Select an incident to dispatch ${r.name}', 'info');">Assign</button>`
      : `<button class="btn btn-outline btn-sm" onclick="releaseUnit(${r.id})">Release Unit</button>`;

    return `
      <tr>
        <td><strong style="color:var(--accent-cyan); font-family:var(--font-mono);">${r.resource_code}</strong></td>
        <td><strong style="color:#fff;">${r.name}</strong></td>
        <td><span class="badge badge-info">${r.type.replace('_', ' ').toUpperCase()}</span></td>
        <td>${capsHtml}</td>
        <td><span style="font-size:0.75rem; color:var(--text-muted);">${r.base_station}</span></td>
        <td>${statusBadge}</td>
        <td>${assignedHtml}</td>
        <td>${actionBtn}</td>
      </tr>
    `;
  }).join('');
}

/**
 * Render Quick Fleet Widget on Command Center
 */
function renderQuickFleetList(resources) {
  const container = document.getElementById('quick-fleet-list');
  if (!container) return;

  if (resources.length === 0) {
    container.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem;">No fleet units found.</div>';
    return;
  }

  container.innerHTML = resources.slice(0, 6).map(r => {
    const isAvail = r.status === 'available';
    return `
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem; padding:0.25rem 0; border-bottom:1px solid var(--border-subtle);">
        <div>
          <span style="color:#fff; font-weight:600;">${r.name}</span>
          <span style="color:var(--text-dim); font-size:0.7rem; margin-left:0.35rem;">(${r.resource_code})</span>
        </div>
        <span class="badge ${isAvail ? 'badge-available' : 'badge-dispatched'}" style="font-size:0.65rem;">
          ${r.status.toUpperCase()}
        </span>
      </div>
    `;
  }).join('');
}

/**
 * Execute Atomic Resource Dispatch
 */
async function dispatchUnitToIncident(incidentId, resourceId, unitName) {
  try {
    const res = await fetch('/api/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_id: incidentId,
        resource_id: resourceId,
        notes: `Tactical dispatch of ${unitName} to incident`,
        dispatcher_name: 'Command Center Dispatcher'
      })
    });

    const data = await res.json();

    if (res.ok) {
      showToast(data.message || `Unit ${unitName} dispatched successfully!`, 'success');
      closeIncidentModal();

      // Refresh data
      await loadResources();
      await loadIncidents();
      await refreshOverviewKPIs();
      if (typeof loadAlerts === 'function') loadAlerts(false);
      if (typeof loadRecentAuditFeed === 'function') loadRecentAuditFeed();
    } else {
      showToast(data.error || 'Dispatch assignment conflict. Resource may no longer be available.', 'error');
      // Re-fetch detail to update modal state
      showIncidentDetail(incidentId);
    }
  } catch (err) {
    showToast('Failed to execute dispatch command.', 'error');
  }
}

/**
 * Release a Dispatched Unit back to Available
 */
async function releaseUnit(resourceId, incidentIdToReload = null) {
  try {
    const res = await fetch('/api/dispatch/release', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resource_id: resourceId,
        notes: 'Mission completed, unit returning to base station'
      })
    });

    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Unit returned to Available status.', 'info');

      await loadResources();
      await loadIncidents();
      await refreshOverviewKPIs();
      if (typeof loadRecentAuditFeed === 'function') loadRecentAuditFeed();

      if (incidentIdToReload) {
        showIncidentDetail(incidentIdToReload);
      }
    } else {
      showToast(data.error || 'Failed to release resource.', 'error');
    }
  } catch (err) {
    showToast('Network error while releasing resource.', 'error');
  }
}
