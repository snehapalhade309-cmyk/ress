/**
 * RESQAI - Alert Center & Emergency Notification Broadcasts
 */

let showUnackOnly = false;

document.addEventListener('DOMContentLoaded', () => {
  const btnToggle = document.getElementById('btn-toggle-unack');
  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      showUnackOnly = !showUnackOnly;
      btnToggle.textContent = showUnackOnly ? 'Show All Alerts' : 'Show Unacknowledged Only';
      loadAlerts(false);
    });
  }
});

/**
 * Fetch and Render Alerts
 */
async function loadAlerts(isInitial = false) {
  try {
    const url = `/api/alerts${showUnackOnly ? '?unacknowledged_only=1' : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Alerts fetch failed');
    const alerts = await res.json();
    AppState.alerts = alerts;

    // Update unacknowledged count
    const unackCount = alerts.filter(a => !a.is_acknowledged).length;
    const badge = document.getElementById('header-alert-count');
    const navBadge = document.getElementById('nav-badge-alerts');
    if (badge) badge.textContent = unackCount;
    if (navBadge) navBadge.textContent = unackCount;

    renderAlerts(alerts);
  } catch (err) {
    console.error('Error loading alerts:', err);
  }
}

/**
 * Render Alerts Feed
 */
function renderAlerts(alerts) {
  const container = document.getElementById('alerts-container');
  if (!container) return;

  if (alerts.length === 0) {
    container.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding:2rem;">No active emergency alerts at this time.</div>';
    return;
  }

  container.innerHTML = alerts.map(a => {
    const sev = a.severity.toLowerCase();
    const time = a.created_at ? new Date(a.created_at).toLocaleString() : '';
    const isAck = Boolean(a.is_acknowledged);

    // Simulated regional translations for disaster communication
    let regionalHtml = '';
    if (sev === 'critical') {
      regionalHtml = `
        <div style="margin-top:0.5rem; font-size:0.75rem; border-top:1px dashed var(--border-subtle); padding-top:0.4rem; color:var(--text-dim);">
          <div><strong style="color:var(--text-muted);">HI:</strong> तत्काल चेतावनी: बाढ़ प्रभावित क्षेत्रों से तुरंत सुरक्षित स्थान पर जाएं।</div>
          <div style="margin-top:2px;"><strong style="color:var(--text-muted);">MR:</strong> तातडीचा इशारा: पूरग्रस्त भागातील नागरिकांनी सुरक्षित निवारा केंद्रात जावे.</div>
        </div>
      `;
    }

    return `
      <div style="background:var(--bg-surface); border:1px solid ${isAck ? 'var(--border-subtle)' : `var(--sev-${sev})`}; border-left:4px solid var(--sev-${sev}); border-radius:var(--radius-md); padding:1rem; margin-bottom:0.75rem; opacity:${isAck ? '0.75' : '1'};">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
              <span class="badge badge-${sev}">${a.severity.toUpperCase()}</span>
              <strong style="color:#fff; font-size:0.95rem;">${a.title}</strong>
            </div>
            <p style="font-size:0.82rem; color:var(--text-main); margin-top:0.35rem; line-height:1.4;">${a.message}</p>
            ${regionalHtml}
            <div style="font-size:0.72rem; color:var(--text-dim); margin-top:0.5rem;">
              Source: <strong>${a.source}</strong> | Emitted: ${time}
            </div>
          </div>
          <div>
            ${isAck
              ? '<span class="badge" style="background:rgba(16,185,129,0.1); color:var(--sev-low); font-size:0.68rem;">ACKNOWLEDGED</span>'
              : `<button class="btn btn-secondary btn-sm" onclick="acknowledgeAlert(${a.id})">Acknowledge</button>`
            }
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Acknowledge an Alert
 */
async function acknowledgeAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
    if (res.ok) {
      showToast('Emergency alert acknowledged.', 'info');
      await loadAlerts(false);
      await refreshOverviewKPIs();
    }
  } catch (err) {
    showToast('Failed to acknowledge alert.', 'error');
  }
}
