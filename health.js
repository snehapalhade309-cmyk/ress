/**
 * RESQAI - System Health & Integration Registry Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const btnProbe = document.getElementById('btn-refresh-health');
  if (btnProbe) {
    btnProbe.addEventListener('click', runHealthProbe);
  }

  const btnReset = document.getElementById('btn-reset-demo');
  if (btnReset) {
    btnReset.addEventListener('click', handleResetDemo);
  }
});

/**
 * Execute Diagnostic Probe against API
 */
async function runHealthProbe() {
  const tbody = document.getElementById('health-table-body');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--accent-cyan);">Running live network and database probes...</td></tr>';

  try {
    const res = await fetch('/api/health');
    if (!res.ok) throw new Error('Health probe failed');
    const data = await res.json();
    const itg = data.integrations || {};

    const rows = [
      {
        name: 'SQLite Database & WAL Engine',
        status: itg.database?.status === 'healthy' ? 'operational' : 'error',
        latency: '< 1 ms',
        endpoint: 'Local data/resqai.db',
        auth: 'Local File Lock',
        rate_limit: 'Unlimited (Concurrent WAL)',
        attr: 'SQLite3 Embedded Database Engine'
      },
      {
        name: itg.osm_tiles?.name || 'OpenStreetMap Tile CDN',
        status: itg.osm_tiles?.status || 'operational',
        latency: '~45 ms',
        endpoint: itg.osm_tiles?.endpoint || 'https://tile.openstreetmap.org',
        auth: 'None Required',
        rate_limit: 'Standard OSM Tile Usage Policy',
        attr: itg.osm_tiles?.attribution || '© OpenStreetMap contributors'
      },
      {
        name: itg.weather_api?.name || 'Open-Meteo Weather API',
        status: itg.weather_api?.status || 'operational',
        latency: itg.weather_api?.latency_ms ? `${itg.weather_api.latency_ms} ms` : '~60 ms',
        endpoint: itg.weather_api?.endpoint || 'https://api.open-meteo.com/v1/forecast',
        auth: 'None Required',
        rate_limit: itg.weather_api?.rate_limit || '10,000 / day',
        attr: itg.weather_api?.attribution || 'Open-Meteo CC BY 4.0'
      },
      {
        name: itg.routing_engine?.name || 'OSRM Public Router',
        status: itg.routing_engine?.status || 'operational',
        latency: itg.routing_engine?.latency_ms ? `${itg.routing_engine.latency_ms} ms` : '~85 ms',
        endpoint: itg.routing_engine?.endpoint || 'http://router.project-osrm.org',
        auth: 'None Required',
        rate_limit: itg.routing_engine?.rate_limit || 'Public Demo Tier',
        attr: itg.routing_engine?.attribution || 'OSRM Project'
      },
      {
        name: itg.geocoding_service?.name || 'Nominatim Public Geocoding',
        status: itg.geocoding_service?.status || 'operational',
        latency: itg.geocoding_service?.latency_ms ? `${itg.geocoding_service.latency_ms} ms` : '~95 ms',
        endpoint: itg.geocoding_service?.endpoint || 'https://nominatim.openstreetmap.org',
        auth: 'None Required',
        rate_limit: itg.geocoding_service?.rate_limit || '1 req/sec',
        attr: itg.geocoding_service?.attribution || '© OpenStreetMap contributors'
      },
      {
        name: itg.ai_service?.name || 'Local Ollama AI Daemon',
        status: itg.ai_service?.status || 'offline',
        latency: itg.ai_service?.latency_ms ? `${itg.ai_service.latency_ms} ms` : 'N/A',
        endpoint: itg.ai_service?.endpoint || 'http://localhost:11434',
        auth: 'Local Host Access',
        rate_limit: 'Hardware Bound',
        attr: 'Ollama local inference (Heuristic fallback active)'
      }
    ];

    tbody.innerHTML = rows.map(r => {
      let badgeClass = 'badge-low';
      let dotColor = 'var(--sev-low)';
      if (r.status === 'degraded' || r.status === 'untested') {
        badgeClass = 'badge-medium';
        dotColor = 'var(--sev-medium)';
      } else if (r.status === 'offline' || r.status === 'error') {
        badgeClass = 'badge-reported';
        dotColor = 'var(--text-dim)';
      }

      return `
        <tr>
          <td><strong style="color:#fff;">${r.name}</strong></td>
          <td>
            <div style="display:flex; align-items:center; gap:0.4rem;">
              <div style="width:8px; height:8px; border-radius:50%; background:${dotColor};"></div>
              <span class="badge ${badgeClass}">${r.status.toUpperCase()}</span>
            </div>
          </td>
          <td><span style="font-family:var(--font-mono); color:var(--accent-cyan);">${r.latency}</span></td>
          <td><code style="font-size:0.72rem; color:var(--text-muted);">${r.endpoint}</code></td>
          <td><span style="font-size:0.75rem; color:${r.auth === 'None Required' ? 'var(--sev-low)' : 'var(--text-muted)'}; font-weight:600;">${r.auth}</span></td>
          <td><span style="font-size:0.72rem; color:var(--text-dim);">${r.rate_limit}</span></td>
          <td><span style="font-size:0.72rem; color:var(--text-muted);">${r.attr}</span></td>
        </tr>
      `;
    }).join('');

    showToast('Integration telemetry updated.', 'info');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--sev-critical);">Failed to probe system health.</td></tr>';
  }
}

/**
 * Reset Demo Database Handler
 */
async function handleResetDemo() {
  const confirmed = confirm('Are you sure you want to reset the database to clean initial seed data? This will clear any live test incidents and reset fleet assignments.');
  if (!confirmed) return;

  try {
    const res = await fetch('/api/system/reset-demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true })
    });

    if (res.ok) {
      showToast('Database reset to clean emergency scenario dataset.', 'success');
      await loadInitialData();
      switchTab('tab-overview');
    } else {
      showToast('Reset failed.', 'error');
    }
  } catch (err) {
    showToast('Network error during database reset.', 'error');
  }
}
