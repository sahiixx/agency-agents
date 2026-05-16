/**
 * Dubai Real Estate Dashboard — Frontend Controller
 * Fetches LIVE data from /api/* endpoints (real DLD data)
 * Author: Frontend Dev Agent (Kimi CLI)
 */

const API_BASE = '';
let marketData = null;

// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  await loadMarketData();
  setupVisaForm();
});

// ── Data Loading ────────────────────────────────────────────────────────────

async function loadMarketData() {
  try {
    const res = await fetch(`${API_BASE}/api/market-data`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    marketData = await res.json();
    renderStats();
    renderAreaCards();
    renderPriceChart();
    populateAreaSelect();
  } catch (err) {
    console.error('Failed to load market data:', err);
    showError('Failed to load live market data. Ensure the server is running: python3 api/server.py');
  }
}

// ── Stats Bar ───────────────────────────────────────────────────────────────

function renderStats() {
  const cw = marketData.citywide;
  const fmt = n => new Intl.NumberFormat('en-AE', { maximumFractionDigits: 0 }).format(n);
  const fmtCompact = n => {
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return fmt(n);
  };

  document.getElementById('stat-price').textContent = 'AED ' + fmt(cw.avg_price_sqft);
  document.getElementById('stat-yoy').textContent = '▲ ' + cw.yoy_change_percent + '% YoY';
  document.getElementById('stat-trans').textContent = fmtCompact(cw.total_transactions_2024);
  document.getElementById('stat-yield').textContent = cw.avg_apartment_yield_gross + '%';
  document.getElementById('stat-value').textContent = 'AED ' + cw.total_value_2024_billion + 'B';

  document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('loading'));
}

// ── Area Cards ──────────────────────────────────────────────────────────────

function renderAreaCards() {
  const container = document.getElementById('area-cards');
  const tierClasses = {
    luxury: 'tier-luxury',
    premium: 'tier-premium',
    mid: 'tier-mid',
    value: 'tier-value',
    budget: 'tier-value',
  };

  container.innerHTML = marketData.areas.map(area => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${area.name}</div>
          <div style="font-size:0.8rem;color:var(--slate-400);margin-top:0.25rem;">${area.highlight}</div>
        </div>
        <span class="card-tier ${tierClasses[area.tier] || 'tier-mid'}">${area.tier}</span>
      </div>
      <div class="card-metrics">
        <div class="metric">
          <span class="metric-label">Price / sqft</span>
          <span class="metric-value" style="color:var(--gold-400);">AED ${area.price_sqft.toLocaleString()}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Gross Yield</span>
          <span class="metric-value" style="color:var(--emerald-400);">${area.yield_gross}%</span>
        </div>
        <div class="metric">
          <span class="metric-label">YoY Change</span>
          <span class="metric-value" style="color:${area.yoy_change > 15 ? 'var(--rose-500)' : 'var(--emerald-400)'};">${area.yoy_change > 0 ? '+' : ''}${area.yoy_change}%</span>
        </div>
        <div class="metric">
          <span class="metric-label">Typical Range</span>
          <span class="metric-value" style="font-size:0.9rem;">${area.typical_range}</span>
        </div>
      </div>
      <div style="font-size:0.75rem;color:var(--slate-500);border-top:1px solid var(--slate-700);padding-top:0.75rem;margin-top:0.5rem;">
        Types: ${area.property_types.join(', ')}
      </div>
    </div>
  `).join('');
}

// ── Price Chart ─────────────────────────────────────────────────────────────

function renderPriceChart() {
  const container = document.getElementById('price-chart');
  const maxPrice = Math.max(...marketData.areas.map(a => a.price_sqft));

  container.innerHTML = marketData.areas.map(area => {
    const pct = (area.price_sqft / maxPrice) * 100;
    const barClass = area.tier === 'luxury' ? 'gold' : area.tier === 'value' ? 'emerald' : 'blue';
    return `
      <div class="bar-row">
        <div class="bar-label">${area.name}</div>
        <div class="bar-track">
          <div class="bar-fill ${barClass}" style="width:${pct}%;min-width:40px;">
            <span class="bar-value">AED ${(area.price_sqft / 1000).toFixed(1)}K</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ── ROI Calculator ──────────────────────────────────────────────────────────

function populateAreaSelect() {
  const sel = document.getElementById('calc-area');
  sel.innerHTML = marketData.areas.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
}

async function calculateROI() {
  const resultDiv = document.getElementById('roi-result');
  resultDiv.innerHTML = '<div class="success"><span class="spinner"></span>Calculating with real Dubai costs...</div>';

  const payload = {
    property_price: parseFloat(document.getElementById('calc-price').value),
    down_payment_percent: parseFloat(document.getElementById('calc-down').value),
    mortgage_rate: parseFloat(document.getElementById('calc-rate').value),
    years: parseInt(document.getElementById('calc-years').value),
    annual_rent_growth: parseFloat(document.getElementById('calc-growth').value),
    area_id: document.getElementById('calc-area').value,
  };

  try {
    const res = await fetch(`${API_BASE}/api/calculate-roi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.error) {
      resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
      return;
    }

    resultDiv.innerHTML = `
      <div class="result-panel">
        <div class="result-grid">
          <div class="result-item">
            <div class="result-value">${data.roi_percent}%</div>
            <div class="result-label">Total ROI</div>
          </div>
          <div class="result-item">
            <div class="result-value">${data.annualized_roi_percent}%</div>
            <div class="result-label">Annualized</div>
          </div>
          <div class="result-item">
            <div class="result-value">AED ${(data.total_profit / 1e6).toFixed(2)}M</div>
            <div class="result-label">Total Profit</div>
          </div>
          <div class="result-item">
            <div class="result-value">${data.break_even_years} yrs</div>
            <div class="result-label">Break Even</div>
          </div>
        </div>
        <div style="margin-top:1.5rem;padding-top:1.5rem;border-top:1px solid var(--slate-700);display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:1rem;font-size:0.85rem;color:var(--slate-400);">
          <div>Upfront: <strong style="color:var(--slate-100);">AED ${(data.total_upfront / 1e6).toFixed(2)}M</strong></div>
          <div>Monthly Mortgage: <strong style="color:var(--slate-100);">AED ${data.monthly_mortgage.toLocaleString()}</strong></div>
          <div>Net Annual Rent: <strong style="color:var(--emerald-400);">AED ${data.annual_rent_net.toLocaleString()}</strong></div>
          <div>Est. Appreciation: <strong style="color:var(--gold-400);">AED ${(data.appreciation / 1e6).toFixed(2)}M</strong></div>
        </div>
      </div>
    `;
  } catch (err) {
    resultDiv.innerHTML = `<div class="error">Calculation failed: ${err.message}</div>`;
  }
}

// ── Golden Visa ─────────────────────────────────────────────────────────────

function setupVisaForm() {
  const status = document.getElementById('visa-status');
  const mortgage = document.getElementById('visa-mortgage');
  const paidGroup = document.getElementById('paid-group');

  function update() {
    const showPaid = status.value === 'offplan' || mortgage.value === 'true';
    paidGroup.style.display = showPaid ? 'block' : 'none';
  }
  status.addEventListener('change', update);
  mortgage.addEventListener('change', update);
  update();
}

async function checkVisa() {
  const resultDiv = document.getElementById('visa-result');
  resultDiv.innerHTML = '<div class="success"><span class="spinner"></span>Checking DLD rules...</div>';

  const payload = {
    property_price: parseFloat(document.getElementById('visa-price').value),
    is_offplan: document.getElementById('visa-status').value === 'offplan',
    is_mortgaged: document.getElementById('visa-mortgage').value === 'true',
    paid_amount: parseFloat(document.getElementById('visa-paid').value) || 0,
  };

  try {
    const res = await fetch(`${API_BASE}/api/check-visa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    const statusClass = data.eligible ? 'visa-eligible' : 'visa-ineligible';
    const icon = data.eligible ? '✅' : '❌';
    resultDiv.innerHTML = `
      <div class="visa-status ${statusClass}">
        ${icon} ${data.eligible ? 'ELIGIBLE' : 'NOT ELIGIBLE'} — ${data.visa_type || ''}
      </div>
      <p style="margin-top:0.75rem;color:var(--slate-400);font-size:0.875rem;">${data.reason}</p>
    `;
  } catch (err) {
    resultDiv.innerHTML = `<div class="error">Check failed: ${err.message}</div>`;
  }
}

// ── Property Matcher ────────────────────────────────────────────────────────

async function matchProperties() {
  const resultDiv = document.getElementById('match-result');
  resultDiv.innerHTML = '<div class="success"><span class="spinner"></span>Finding optimal districts...</div>';

  const payload = {
    budget_max: parseFloat(document.getElementById('match-budget').value),
    property_type: document.getElementById('match-type').value || null,
    min_yield: parseFloat(document.getElementById('match-yield').value),
    preferred_areas: [],
  };

  try {
    const res = await fetch(`${API_BASE}/api/match-property`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!data.matches || data.matches.length === 0) {
      resultDiv.innerHTML = '<div class="error">No matches found. Try adjusting your criteria.</div>';
      return;
    }

    resultDiv.innerHTML = `
      <div style="margin-top:1.5rem;">
        <h3 style="color:var(--slate-100);margin-bottom:1rem;font-size:1.125rem;">Top ${data.matches.length} Matches</h3>
        <div class="grid grid-cols-1" style="gap:0.75rem;">
          ${data.matches.map((m, i) => `
            <div class="card" style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1.5rem;">
              <div style="display:flex;align-items:center;gap:1rem;">
                <div style="width:36px;height:36px;background:var(--slate-700);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--gold-400);">${i + 1}</div>
                <div>
                  <div style="font-weight:700;color:var(--slate-100);">${m.name}</div>
                  <div style="font-size:0.8rem;color:var(--slate-400);">${m.affordable_sqft} sqft affordable · ${m.yield_gross}% yield</div>
                </div>
              </div>
              <div style="text-align:right;">
                <div style="font-weight:800;color:var(--gold-400);font-family:var(--font-mono);">AED ${m.price_sqft.toLocaleString()}/sqft</div>
                <div style="font-size:0.75rem;color:var(--emerald-400);">Score: ${m.match_score}/100</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } catch (err) {
    resultDiv.innerHTML = `<div class="error">Matching failed: ${err.message}</div>`;
  }
}

// ── Utilities ───────────────────────────────────────────────────────────────

function showError(msg) {
  const div = document.createElement('div');
  div.className = 'error';
  div.textContent = msg;
  document.querySelector('.hero .container').appendChild(div);
}
