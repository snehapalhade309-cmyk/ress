/**
 * RESQAI - Analytics & Visualization Engine (Chart.js)
 */

let chartTypes = null;
let chartRisk = null;
let chartStatus = null;
let chartFleet = null;

function renderAnalyticsCharts() {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js library not loaded yet.');
    return;
  }

  const incidents = AppState.incidents || [];
  const resources = AppState.resources || [];

  renderIncidentTypesChart(incidents);
  renderRiskTiersChart(incidents);
  renderStatusFunnelChart(incidents);
  renderFleetUsageChart(resources);
}

function renderIncidentTypesChart(incidents) {
  const ctx = document.getElementById('chart-incident-types');
  if (!ctx) return;

  const typeCounts = {
    'Flood': 0,
    'Landslide': 0,
    'Fire': 0,
    'Accident': 0,
    'Severe Weather': 0,
    'Earthquake': 0
  };

  incidents.forEach(inc => {
    const t = (inc.type || '').toLowerCase();
    if (t === 'flood') typeCounts['Flood']++;
    else if (t === 'landslide') typeCounts['Landslide']++;
    else if (t === 'fire') typeCounts['Fire']++;
    else if (t === 'accident') typeCounts['Accident']++;
    else if (t === 'severe_weather') typeCounts['Severe Weather']++;
    else if (t === 'earthquake') typeCounts['Earthquake']++;
  });

  if (chartTypes) chartTypes.destroy();

  chartTypes = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: Object.keys(typeCounts),
      datasets: [{
        data: Object.values(typeCounts),
        backgroundColor: [
          '#00e5ff', // Flood - Cyan
          '#f59e0b', // Landslide - Amber
          '#ef4444', // Fire - Crimson
          '#0284c7', // Accident - Blue
          '#a855f7', // Weather - Purple
          '#10b981'  // Earthquake - Emerald
        ],
        borderColor: '#0b1329',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#94a3b8', font: { size: 11 } }
        }
      }
    }
  });
}

function renderRiskTiersChart(incidents) {
  const ctx = document.getElementById('chart-risk-tiers');
  if (!ctx) return;

  const tiers = { 'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0 };
  incidents.forEach(inc => {
    const cat = inc.risk_category || 'Low';
    if (tiers[cat] !== undefined) tiers[cat]++;
  });

  if (chartRisk) chartRisk.destroy();

  chartRisk = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Critical (78-100)', 'High (55-77)', 'Medium (30-54)', 'Low (5-29)'],
      datasets: [{
        label: 'Active Incidents',
        data: [tiers['Critical'], tiers['High'], tiers['Medium'], tiers['Low']],
        backgroundColor: ['#ef4444', '#f97316', '#eab308', '#10b981'],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
        y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.06)' } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function renderStatusFunnelChart(incidents) {
  const ctx = document.getElementById('chart-status-funnel');
  if (!ctx) return;

  const statuses = { 'Reported': 0, 'Verified': 0, 'Dispatched': 0, 'On Scene': 0, 'Resolved': 0 };
  incidents.forEach(inc => {
    const s = (inc.status || '').toLowerCase();
    if (s === 'reported') statuses['Reported']++;
    else if (s === 'verified') statuses['Verified']++;
    else if (s === 'dispatched') statuses['Dispatched']++;
    else if (s === 'on_scene') statuses['On Scene']++;
    else if (s === 'resolved') statuses['Resolved']++;
  });

  if (chartStatus) chartStatus.destroy();

  chartStatus = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(statuses),
      datasets: [{
        label: 'Count',
        data: Object.values(statuses),
        backgroundColor: '#0284c7',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
        y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.06)' } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function renderFleetUsageChart(resources) {
  const ctx = document.getElementById('chart-fleet-usage');
  if (!ctx) return;

  let avail = 0;
  let disp = 0;
  resources.forEach(r => {
    if (r.status === 'available') avail++;
    else disp++;
  });

  if (chartFleet) chartFleet.destroy();

  chartFleet = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Available (Standby)', 'Dispatched / Deployed'],
      datasets: [{
        data: [avail, disp],
        backgroundColor: ['#10b981', '#f97316'],
        borderColor: '#0b1329',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#94a3b8' }
        }
      }
    }
  });
}
