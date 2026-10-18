/**
 * RESQAI - Incidents Management & Reporting Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  initReportForm();
  initVulnerabilityTagButtons();
});

/**
 * Fetch and Render Incidents
 */
async function loadIncidents() {
  try {
    const res = await fetch('/api/incidents');
    if (!res.ok) throw new Error('Failed to load incidents');
    const incidents = await res.json();
    AppState.incidents = incidents;

    renderOverviewIncidentTable(incidents);
    if (typeof renderMapMarkers === 'function') {
      renderMapMarkers();
    }

    // Update map nav badge
    const badge = document.getElementById('nav-badge-map');
    if (badge) badge.textContent = incidents.length;
  } catch (err) {
    console.error('Error loading incidents:', err);
    const tbody = document.getElementById('overview-incidents-body');
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--sev-critical); padding:2rem;">Failed to load incident stream. Ensure server is running.</td></tr>';
    }
  }
}

/**
 * Render Command Center Priority Table
 */
function renderOverviewIncidentTable(incidents) {
  const tbody = document.getElementById('overview-incidents-body');
  if (!tbody) return;

  if (incidents.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-dim); padding:2rem;">No active incidents reported. All clear.</td></tr>';
    return;
  }

  tbody.innerHTML = incidents.map(inc => {
    const riskCat = (inc.risk_category || 'Low').toLowerCase();
    const score = Number(inc.calculated_risk_score || 0).toFixed(1);

    // Format vulnerability tags
    const vulns = Array.isArray(inc.vulnerability_tags) ? inc.vulnerability_tags : [];
    const vulnsHtml = vulns.length > 0
      ? vulns.map(v => `<span class="badge" style="background:rgba(249,115,22,0.15); color:var(--sev-high); border:1px solid rgba(249,115,22,0.3); font-size:0.65rem; margin-right:3px;">${v.replace('_', ' ')}</span>`).join('')
      : '<span style="color:var(--text-dim); font-size:0.75rem;">None</span>';

    return `
      <tr>
        <td><strong style="color:var(--accent-cyan); font-family:var(--font-mono);">${inc.incident_code}</strong></td>
        <td><span class="badge badge-info">${inc.type.toUpperCase()}</span></td>
        <td>
          <div style="font-weight:600; color:#fff;">${inc.title}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${inc.location_name}</div>
        </td>
        <td>
          <div style="display:flex; align-items:center; gap:0.4rem;">
            <span class="badge badge-${riskCat}">${score}</span>
            <span style="font-size:0.72rem; text-transform:uppercase; font-weight:700; color:var(--sev-${riskCat});">${inc.risk_category}</span>
          </div>
        </td>
        <td><strong>${inc.affected_people || 0}</strong> <span style="color:var(--text-dim); font-size:0.72rem;">civilians</span></td>
        <td>${vulnsHtml}</td>
        <td><span class="badge badge-${inc.status}">${inc.status.replace('_', ' ').toUpperCase()}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="showIncidentDetail(${inc.id})">
            Inspect & Dispatch
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Vulnerability Need Tag Button Toggles
 */
function initVulnerabilityTagButtons() {
  const tagBtns = document.querySelectorAll('.vuln-tag-btn');
  tagBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      const checkbox = btn.querySelector('input[type="checkbox"]');
      if (checkbox) checkbox.checked = btn.classList.contains('active');
      if (typeof triggerRiskPreview === 'function') triggerRiskPreview();
    });
  });
}

/**
 * Handle Incident Report Form Submission
 */
function initReportForm() {
  const form = document.getElementById('form-report-incident');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('btn-submit-report');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying & Persisting...';

    // Collect vulnerability tags
    const activeTags = [];
    document.querySelectorAll('.vuln-tag-btn.active').forEach(b => {
      activeTags.push(b.getAttribute('data-tag'));
    });

    const payload = {
      type: document.getElementById('rep-type').value,
      reported_severity: document.getElementById('rep-severity').value,
      title: document.getElementById('rep-title').value.trim(),
      location_name: document.getElementById('rep-location').value.trim(),
      latitude: document.getElementById('rep-lat').value || null,
      longitude: document.getElementById('rep-lon').value || null,
      affected_people: document.getElementById('rep-people').value || 0,
      vulnerability_tags: activeTags,
      description: document.getElementById('rep-description').value.trim(),
      reporter_name: document.getElementById('rep-reporter-name').value.trim() || 'Command Station Operator',
      reporter_contact: document.getElementById('rep-reporter-contact').value.trim()
    };

    try {
      const res = await fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        showToast(`Incident ${data.incident.incident_code} logged! Calculated Risk: ${data.risk_evaluation.score}/100 (${data.risk_evaluation.category})`, 'success');

        // Reset form
        form.reset();
        document.querySelectorAll('.vuln-tag-btn.active').forEach(b => b.classList.remove('active'));

        // Refresh all tables and KPIs
        await loadIncidents();
        await refreshOverviewKPIs();
        if (typeof loadAlerts === 'function') loadAlerts(false);
        if (typeof loadRecentAuditFeed === 'function') loadRecentAuditFeed();

        // Switch to Command Center to view newly added incident
        switchTab('tab-overview');
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to submit incident report.', 'error');
      }
    } catch (err) {
      showToast('Network error while saving incident report.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Incident to Command Net';
    }
  });
}

/**
 * Show Incident Detail & Dispatch Modal
 */
async function showIncidentDetail(incidentId) {
  try {
    const res = await fetch(`/api/incidents/${incidentId}`);
    if (!res.ok) throw new Error('Incident fetch failed');
    const data = await res.json();

    const inc = data.incident;
    const risk = data.risk_evaluation;
    const weather = data.weather;
    const brief = data.decision_brief;
    const recs = data.recommendations || [];
    const assigned = data.assigned_units || [];

    const riskCat = (inc.risk_category || 'Low').toLowerCase();

    // Render Factor Breakdown List
    const factorItems = (risk.factor_breakdown || []).map(f => `
      <div style="display:flex; justify-content:space-between; padding:0.3rem 0; border-bottom:1px solid var(--border-subtle); font-size:0.78rem;">
        <div>
          <strong style="color:#fff;">${f.factor}</strong>
          <div style="font-size:0.72rem; color:var(--text-muted);">${f.description}</div>
        </div>
        <span style="color:var(--accent-cyan); font-weight:700; font-family:var(--font-mono);">+${f.points} pts</span>
      </div>
    `).join('');

    // Render Tactical Recommendations
    let briefContent = '';
    if (brief.tactical_recommendations) {
      briefContent = `
        <div style="background:var(--bg-surface); padding:0.85rem; border-radius:var(--radius-md); margin-top:0.75rem; border:1px solid var(--border-subtle);">
          <div style="font-weight:700; color:var(--accent-cyan); font-size:0.8rem; margin-bottom:0.4rem;">
            ${brief.provider}
          </div>
          <p style="font-size:0.8rem; color:#fff; margin-bottom:0.5rem;">${brief.summary}</p>
          <ul style="padding-left:1.2rem; font-size:0.78rem; color:var(--text-muted); display:flex; flex-direction:column; gap:0.25rem;">
            ${brief.tactical_recommendations.map(r => `<li>${r}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // Render Assigned Units if any
    let assignedHtml = '';
    if (assigned.length > 0) {
      assignedHtml = `
        <div style="margin-top:1rem; padding:0.75rem; background:rgba(249,115,22,0.1); border:1px solid var(--sev-high); border-radius:var(--radius-md);">
          <strong style="color:var(--sev-high); font-size:0.8rem;">Active Units On-Scene:</strong>
          ${assigned.map(u => `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem; font-size:0.78rem;">
              <span>${u.name} (${u.resource_code})</span>
              <button class="btn btn-secondary btn-sm" onclick="releaseUnit(${u.id}, ${inc.id})">Release Unit</button>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Render Recommended Resource Cards
    let recsHtml = '';
    if (recs.length === 0) {
      recsHtml = '<div style="color:var(--text-dim); font-size:0.78rem;">No suitable units currently available in standby queue.</div>';
    } else {
      recsHtml = recs.map(r => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem; background:var(--bg-surface); border-radius:var(--radius-md); border:1px solid var(--border-subtle); margin-top:0.4rem;">
          <div>
            <div style="font-weight:700; color:#fff; font-size:0.82rem;">${r.name} (${r.type.toUpperCase()})</div>
            <div style="font-size:0.72rem; color:var(--text-muted);">
              Distance: <strong style="color:var(--accent-cyan);">${r.distance_km !== null ? r.distance_km + ' km' : 'N/A'}</strong> |
              ETA: <strong style="color:var(--accent-cyan);">${r.eta_minutes !== null ? r.eta_minutes + ' min' : 'Pending GPS'}</strong> |
              Match: <strong style="color:var(--sev-low);">${r.suitability_score}%</strong>
            </div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="dispatchUnitToIncident(${inc.id}, ${r.resource_id}, '${r.name}')">
            Dispatch Unit
          </button>
        </div>
      `).join('');
    }

    const modalHtml = `
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; border-bottom:1px solid var(--border-subtle); padding-bottom:0.75rem;">
          <div>
            <h3 style="color:#fff; font-size:1.1rem; margin-bottom:0.2rem;">${inc.incident_code}: ${inc.title}</h3>
            <div style="font-size:0.78rem; color:var(--text-muted);">${inc.location_name} | Reported by ${inc.reporter_name || 'Civil Defense'}</div>
          </div>
          <div style="display:flex; gap:0.5rem; align-items:center;">
            <span class="badge badge-${riskCat}">${inc.calculated_risk_score} ${inc.risk_category}</span>
            <select class="form-control" style="width:130px; padding:0.25rem 0.5rem; font-size:0.75rem;" onchange="updateStatus(${inc.id}, this.value)">
              <option value="reported" ${inc.status === 'reported' ? 'selected' : ''}>Reported</option>
              <option value="verified" ${inc.status === 'verified' ? 'selected' : ''}>Verified</option>
              <option value="dispatched" ${inc.status === 'dispatched' ? 'selected' : ''}>Dispatched</option>
              <option value="on_scene" ${inc.status === 'on_scene' ? 'selected' : ''}>On Scene</option>
              <option value="resolved" ${inc.status === 'resolved' ? 'selected' : ''}>Resolved</option>
            </select>
          </div>
        </div>

        <p style="font-size:0.82rem; color:var(--text-main); line-height:1.5; margin-bottom:1rem;">
          ${inc.description || 'No situational narrative provided.'}
        </p>

        <!-- Weather snippet if available -->
        ${weather ? `
          <div style="display:flex; gap:1.5rem; padding:0.6rem 0.85rem; background:rgba(0,229,255,0.08); border-radius:var(--radius-md); font-size:0.75rem; margin-bottom:1rem;">
            <div><strong>Condition:</strong> ${weather.condition}</div>
            <div><strong>Temp:</strong> ${weather.temperature}°C</div>
            <div><strong>Precipitation:</strong> ${weather.precipitation} mm/hr</div>
            <div><strong>Wind:</strong> ${weather.wind_speed} km/h</div>
          </div>
        ` : ''}

        <!-- Decision Brief -->
        ${briefContent}

        ${assignedHtml}

        <!-- Smart Dispatch Section -->
        <div style="margin-top:1.25rem;">
          <h4 style="font-size:0.85rem; font-weight:700; color:#fff; margin-bottom:0.4rem;">
            Recommended Response Units (Suitability Ranked)
          </h4>
          <div style="display:flex; flex-direction:column; gap:0.35rem;">
            ${recsHtml}
          </div>
        </div>

        <!-- Risk Factor Breakdown -->
        <div style="margin-top:1.25rem;">
          <h4 style="font-size:0.85rem; font-weight:700; color:#fff; margin-bottom:0.4rem;">
            Transparent Heuristic Risk Factor Breakdown
          </h4>
          <div style="background:var(--bg-surface); padding:0.75rem; border-radius:var(--radius-md);">
            ${factorItems}
          </div>
        </div>
      </div>
    `;

    openIncidentModal(modalHtml);
  } catch (err) {
    showToast('Failed to retrieve incident details.', 'error');
  }
}

/**
 * Update incident status
 */
async function updateStatus(incidentId, newStatus) {
  try {
    const res = await fetch(`/api/incidents/${incidentId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, actor: 'Command Center Operator' })
    });
    if (res.ok) {
      showToast(`Incident status updated to ${newStatus.toUpperCase()}`, 'info');
      loadIncidents();
      refreshOverviewKPIs();
    }
  } catch (err) {
    showToast('Status update failed.', 'error');
  }
}
