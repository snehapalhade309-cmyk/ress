/**
 * RESQAI - Real-Time AI Risk Scoring Preview Controller
 */

let riskPreviewTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  initLiveRiskListeners();
  triggerRiskPreview(); // initial preview calculation
});

function initLiveRiskListeners() {
  const fields = ['rep-type', 'rep-severity', 'rep-people', 'rep-lat', 'rep-lon'];
  fields.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => triggerRiskPreview());
      el.addEventListener('change', () => triggerRiskPreview());
    }
  });
}

function triggerRiskPreview() {
  clearTimeout(riskPreviewTimer);
  riskPreviewTimer = setTimeout(async () => {
    const activeTags = [];
    document.querySelectorAll('.vuln-tag-btn.active').forEach(b => {
      activeTags.push(b.getAttribute('data-tag'));
    });

    const payload = {
      type: document.getElementById('rep-type')?.value || 'flood',
      reported_severity: document.getElementById('rep-severity')?.value || 'moderate',
      affected_people: document.getElementById('rep-people')?.value || 0,
      vulnerability_tags: activeTags,
      latitude: document.getElementById('rep-lat')?.value || null,
      longitude: document.getElementById('rep-lon')?.value || null
    };

    try {
      const res = await fetch('/api/incidents/evaluate-risk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        updateRiskPreviewUI(data.risk, data.weather_snapshot);
      }
    } catch (err) {
      console.warn('Risk preview calculation error:', err);
    }
  }, 250);
}

function updateRiskPreviewUI(risk, weather) {
  if (!risk) return;

  const scoreEl = document.getElementById('preview-risk-score');
  const badgeEl = document.getElementById('preview-risk-badge');
  const barEl = document.getElementById('preview-risk-bar');
  const factorsEl = document.getElementById('preview-factor-list');
  const weatherEl = document.getElementById('preview-weather-box');

  const cat = (risk.category || 'Low').toLowerCase();
  const score = risk.score.toFixed(1);

  // Update Score and Color
  scoreEl.textContent = score;
  scoreEl.style.color = `var(--sev-${cat})`;

  // Update Badge
  badgeEl.className = `badge badge-${cat}`;
  badgeEl.textContent = `${risk.category.toUpperCase()} RISK`;

  // Update Fill Bar
  barEl.style.width = `${Math.min(100, Math.max(5, risk.score))}%`;
  barEl.style.background = `var(--sev-${cat})`;

  // Update Factor Breakdown
  if (factorsEl && risk.factor_breakdown) {
    factorsEl.innerHTML = risk.factor_breakdown.map(f => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.25rem 0; border-bottom:1px solid rgba(255,255,255,0.05);">
        <span style="color:var(--text-main); font-size:0.75rem;">${f.factor}</span>
        <span style="color:var(--accent-cyan); font-weight:700; font-family:var(--font-mono); font-size:0.75rem;">+${f.points}</span>
      </div>
    `).join('');
  }

  // Update Weather Context Box
  if (weatherEl) {
    if (weather) {
      weatherEl.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:0.4rem;">
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Atmospheric Condition:</span>
            <strong style="color:#fff;">${weather.condition}</strong>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Temperature:</span>
            <strong style="color:var(--accent-cyan);">${weather.temperature}${weather.temperature_unit}</strong>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Precipitation:</span>
            <strong style="color:${weather.precipitation > 10 ? 'var(--sev-critical)' : 'var(--accent-cyan)'};">${weather.precipitation} ${weather.precipitation_unit}</strong>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Wind Speed:</span>
            <strong style="color:var(--accent-cyan);">${weather.wind_speed} ${weather.wind_speed_unit}</strong>
          </div>
          <div style="font-size:0.68rem; color:var(--text-dim); margin-top:0.3rem;">
            Source: ${weather.source}
          </div>
        </div>
      `;
    } else {
      weatherEl.innerHTML = '<div style="color:var(--text-dim); font-size:0.78rem;">Enter GPS coordinates or click on the Live Map to query localized Open-Meteo weather factors.</div>';
    }
  }
}
