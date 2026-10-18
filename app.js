/**
 * RESQAI - Main Application Controller & State
 */

const AppState = {
  activeTab: 'tab-overview',
  incidents: [],
  resources: [],
  shelters: [],
  alerts: [],
  weather: null,
  activeRoutePolyline: null,
  selectedCoords: null
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initNavigation();
  initHeaderWeather();
  initQuickActions();

  // Load core application datasets
  loadInitialData();

  // Periodic polling every 30 seconds for live command center telemetry
  setInterval(() => {
    refreshOverviewKPIs();
    if (typeof loadAlerts === 'function') loadAlerts(false);
  }, 30000);
});

/**
 * Live Clocks (UTC and Local System Time)
 */
function initClock() {
  const clockTime = document.getElementById('clock-time');
  const clockDate = document.getElementById('clock-date');

  function update() {
    const now = new Date();
    const utcHours = String(now.getUTCHours()).padStart(2, '0');
    const utcMinutes = String(now.getUTCMinutes()).padStart(2, '0');
    const utcSeconds = String(now.getUTCSeconds()).padStart(2, '0');
    
    clockTime.textContent = `${utcHours}:${utcMinutes}:${utcSeconds} UTC`;
    clockDate.textContent = now.toISOString().split('T')[0];
  }

  update();
  setInterval(update, 1000);
}

/**
 * Tab Navigation Controller
 */
function initNavigation() {
  const navLinks = document.querySelectorAll('.nav-link[data-tab]');
  
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const tabId = link.getAttribute('data-tab');
      switchTab(tabId);
    });
  });

  // Overview quick action button
  const btnGotoReport = document.getElementById('btn-goto-report');
  if (btnGotoReport) {
    btnGotoReport.addEventListener('click', () => switchTab('tab-report'));
  }
}

function switchTab(tabId) {
  AppState.activeTab = tabId;

  // Update nav links
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', l.getAttribute('data-tab') === tabId);
  });

  // Update tab panes
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === tabId);
  });

  // If switched to map, invalidate Leaflet map size to ensure full container render
  if (tabId === 'tab-map' && window.resqaiMap) {
    setTimeout(() => {
      window.resqaiMap.invalidateSize();
    }, 150);
  }

  // Refresh tab-specific data
  if (tabId === 'tab-analytics' && typeof renderAnalyticsCharts === 'function') {
    renderAnalyticsCharts();
  }
  if (tabId === 'tab-health' && typeof runHealthProbe === 'function') {
    runHealthProbe();
  }
}

/**
 * Header Live Weather Pill
 */
async function initHeaderWeather() {
  try {
    const res = await fetch('/api/weather?lat=18.5204&lon=73.8567');
    if (res.ok) {
      const data = await res.json();
      AppState.weather = data;
      document.getElementById('weather-temp').textContent = `${data.temperature}${data.temperature_unit}`;
      document.getElementById('weather-cond').textContent = data.condition;
    }
  } catch (err) {
    console.warn('Header weather fetch error:', err);
    document.getElementById('weather-temp').textContent = '26°C';
    document.getElementById('weather-cond').textContent = 'Baseline';
  }
}

/**
 * Quick Header Action Triggers
 */
function initQuickActions() {
  document.getElementById('btn-quick-report').addEventListener('click', () => {
    switchTab('tab-report');
  });

  document.getElementById('btn-header-alerts').addEventListener('click', () => {
    switchTab('tab-alerts');
  });

  document.getElementById('btn-refresh-overview').addEventListener('click', () => {
    refreshOverviewKPIs();
    loadIncidents();
    loadRecentAuditFeed();
    showToast('Command Center KPIs synchronized.', 'info');
  });

  // Modal close handlers
  document.getElementById('modal-inc-close').addEventListener('click', closeIncidentModal);
  document.getElementById('modal-inc-btn-close').addEventListener('click', closeIncidentModal);
}

/**
 * Initial Data Loading
 */
async function loadInitialData() {
  await Promise.allSettled([
    refreshOverviewKPIs(),
    loadIncidents(),
    loadResources(),
    loadShelters(),
    loadAlerts(true),
    loadRecentAuditFeed()
  ]);
}

/**
 * Refresh Command Center KPI Cards
 */
async function refreshOverviewKPIs() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();

    // Incidents KPI
    document.getElementById('kpi-active-incidents').textContent = stats.incidents.active;
    document.getElementById('kpi-critical-sub').textContent = `${stats.incidents.critical_active} Critical, ${stats.incidents.high_active} High`;

    // Fleet KPI
    document.getElementById('kpi-avail-resources').textContent = stats.resources.available;
    document.getElementById('kpi-fleet-sub').textContent = `${stats.resources.dispatched} Dispatched / ${stats.resources.total} Total`;
    document.getElementById('nav-badge-dispatch').textContent = stats.resources.available;

    // Shelter KPI
    document.getElementById('kpi-shelter-pct').textContent = `${stats.shelters.utilization_pct}%`;
    document.getElementById('kpi-shelter-sub').textContent = `${stats.shelters.current_occupancy.toLocaleString()} / ${stats.shelters.total_capacity.toLocaleString()} Occupied`;

    // Alerts Count
    const unack = stats.alerts.unacknowledged;
    document.getElementById('header-alert-count').textContent = unack;
    document.getElementById('nav-badge-alerts').textContent = unack;

    // Ticker text update
    const ticker = document.getElementById('live-ticker');
    if (stats.incidents.critical_active > 0) {
      ticker.textContent = `ALERT LEVEL 1: ${stats.incidents.critical_active} Critical Emergency in progress. Immediate tactical response active.`;
    } else {
      ticker.textContent = `COMMAND NET ONLINE: ${stats.incidents.active} Active incidents under monitoring. All response nodes nominal.`;
    }
  } catch (err) {
    console.warn('Failed to refresh stats:', err);
  }
}

/**
 * Load Operational Audit Trail Feed
 */
async function loadRecentAuditFeed() {
  const container = document.getElementById('audit-feed-list');
  try {
    const res = await fetch('/api/audit-logs?limit=8');
    if (!res.ok) return;
    const logs = await res.json();

    if (!logs || logs.length === 0) {
      container.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem;">No activity recorded yet.</div>';
      return;
    }

    container.innerHTML = logs.map(l => {
      const time = l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '';
      return `
        <div style="font-size:0.75rem; border-bottom:1px solid var(--border-subtle); padding-bottom:0.35rem;">
          <div style="display:flex; justify-content:space-between; color:var(--text-main);">
            <strong style="color:var(--accent-cyan);">${l.action.replace(/_/g, ' ')}</strong>
            <span style="color:var(--text-dim); font-family:var(--font-mono);">${time}</span>
          </div>
          <div style="color:var(--text-muted); margin-top:0.15rem;">Actor: ${l.actor} | Entity: ${l.entity_type} #${l.entity_id || '-'}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div style="color:var(--text-dim); font-size:0.75rem;">Audit log feed offline.</div>';
  }
}

/**
 * Toast Notification Helper
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div style="flex:1;">${message}</div>
    <span style="cursor:pointer; font-size:1.1rem; line-height:1;" onclick="this.parentElement.remove()">&times;</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4500);
}

/**
 * Modal Open/Close Helpers
 */
function openIncidentModal(htmlContent) {
  document.getElementById('modal-inc-body').innerHTML = htmlContent;
  document.getElementById('modal-incident-detail').classList.add('active');
}

function closeIncidentModal() {
  document.getElementById('modal-incident-detail').classList.remove('active');
}
