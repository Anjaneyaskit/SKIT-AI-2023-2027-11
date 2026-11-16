/**
 * Dashboard Overview & Nutrition Summary Visualizer
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!api.requireAuth()) return;

  const user = api.getUser() || {};
  const welcomeText = document.getElementById('user-welcome-text');
  const datePicker = document.getElementById('dashboard-date');
  const emptyState = document.getElementById('dashboard-empty-state');
  const contentArea = document.getElementById('dashboard-content');
  const loadingIndicator = document.getElementById('dashboard-loading');

  // Stat Card Elements
  const caloriesVal = document.getElementById('stat-calories-val');
  const caloriesSub = document.getElementById('stat-calories-sub');
  const proteinVal = document.getElementById('stat-protein-val');
  const proteinSub = document.getElementById('stat-protein-sub');
  const ironVal = document.getElementById('stat-iron-val');
  const ironSub = document.getElementById('stat-iron-sub');
  const calciumVal = document.getElementById('stat-calcium-val');
  const calciumSub = document.getElementById('stat-calcium-sub');

  const nutrientTableBody = document.getElementById('nutrient-breakdown-body');

  if (welcomeText) {
    welcomeText.textContent = user.name ? `Welcome back, ${user.name}` : 'Welcome to NutriScan';
  }

  function getLocalDateString() {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  const today = getLocalDateString();
  const urlParams = new URLSearchParams(window.location.search);
  const paramDate = urlParams.get('date');
  const targetDate = paramDate || today;

  if (datePicker) {
    datePicker.value = targetDate;
    datePicker.addEventListener('change', () => loadDailySummary(datePicker.value));
  }

  let chartInstance = null;

  async function loadDailySummary(dateStr) {
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (contentArea) contentArea.style.display = 'none';

    const res = await api.get(`/nutrition/summary?date=${encodeURIComponent(dateStr)}`);
    if (loadingIndicator) loadingIndicator.style.display = 'none';

    if (!res.ok || !res.data.success) {
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    const payload = res.data.data;
    const summary = payload.summary;
    const nutrients = summary.nutrients || {};

    if (summary.item_count === 0) {
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    if (contentArea) contentArea.style.display = 'block';

    // 1. Update Headline Stat Cards
    const ener = nutrients['energy_kcal'] || {};
    caloriesVal.textContent = `${ener.total_amount || 0} kcal`;
    caloriesSub.textContent = ener.rda_value ? `Target: ${ener.rda_value} kcal (${ener.rda_percent}% RDA)` : 'RDA target pending';

    const prot = nutrients['protein_g'] || {};
    proteinVal.textContent = `${prot.total_amount || 0} g`;
    proteinSub.textContent = prot.rda_value ? `Target: ${prot.rda_value} g (${prot.rda_percent}% RDA)` : 'RDA target pending';

    const fe = nutrients['iron_mg'] || {};
    ironVal.textContent = `${fe.total_amount || 0} mg`;
    ironSub.textContent = fe.rda_value ? `Target: ${fe.rda_value} mg (${fe.rda_percent}% RDA)` : 'RDA target pending';

    const ca = nutrients['calcium_mg'] || {};
    calciumVal.textContent = `${ca.total_amount || 0} mg`;
    calciumSub.textContent = ca.rda_value ? `Target: ${ca.rda_value} mg (${ca.rda_percent}% RDA)` : 'RDA target pending';

    // 2. Populate Logged Meals List
    loadDashboardMeals(dateStr);

    // 3. Populate Full Breakdown Table
    if (nutrientTableBody) {
      nutrientTableBody.innerHTML = Object.entries(nutrients).map(([key, item]) => {
        let badgeHtml = '<span class="badge badge-info">Pending Ref</span>';
        let progressWidth = 0;
        let progressColor = 'var(--primary)';

        if (item.rda_percent !== null && item.rda_percent !== undefined) {
          progressWidth = Math.min(item.rda_percent, 100);
          if (item.rda_percent >= 80) {
            badgeHtml = '<span class="badge badge-success">Low Risk (Adequate)</span>';
            progressColor = '#10b981';
          } else if (item.rda_percent >= 50) {
            badgeHtml = '<span class="badge badge-warning">Moderate Risk</span>';
            progressColor = '#f59e0b';
          } else {
            badgeHtml = '<span class="badge badge-danger">High Risk</span>';
            progressColor = '#ef4444';
          }
        }

        const rdaDisplay = item.rda_value ? `${item.rda_value} ${item.unit}` : '<span style="color:#94a3b8;">Pending (TODO)</span>';
        const percentDisplay = item.rda_percent !== null ? `${item.rda_percent}%` : '--';

        return `
          <tr>
            <td>
              <strong>${item.display_name}</strong>
              <div style="font-size:0.75rem; color:#94a3b8;">${item.group}</div>
            </td>
            <td><strong>${item.total_amount}</strong> ${item.unit}</td>
            <td>${rdaDisplay}</td>
            <td style="min-width: 140px;">
              <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:2px;">
                <span>${percentDisplay}</span>
              </div>
              <div class="progress-container">
                <div class="progress-bar" style="width:${progressWidth}%; background:${progressColor};"></div>
              </div>
            </td>
            <td>${badgeHtml}</td>
          </tr>
        `;
      }).join('');
    }

    // 3. Render Chart.js
    renderNutrientChart(nutrients);
  }

  function renderNutrientChart(nutrients) {
    const canvas = document.getElementById('rda-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const chartKeys = ['protein_g', 'iron_mg', 'calcium_mg', 'zinc_mg', 'vitamin_c_mg', 'thiamine_mg', 'riboflavin_mg'];
    const labels = [];
    const values = [];
    const backgroundColors = [];

    chartKeys.forEach(k => {
      const nut = nutrients[k];
      if (nut) {
        labels.push(nut.display_name);
        const p = nut.rda_percent !== null ? nut.rda_percent : 0;
        values.push(p);
        if (p >= 80) backgroundColors.push('rgba(16, 185, 129, 0.85)');
        else if (p >= 50) backgroundColors.push('rgba(245, 158, 11, 0.85)');
        else backgroundColors.push('rgba(239, 68, 68, 0.85)');
      }
    });

    if (chartInstance) {
      chartInstance.destroy();
    }

    chartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '% of Daily ICMR-NIN 2020 RDA Target',
          data: values,
          backgroundColor: backgroundColors,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: 120,
            ticks: {
              callback: val => `${val}%`
            },
            grid: {
              color: '#e2e8f0'
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: context => ` Intake: ${context.parsed.y}% of RDA`
            }
          }
        }
      }
    });
  }

  async function loadDashboardMeals(dateStr) {
    const mealsBody = document.getElementById('dashboard-meals-body');
    if (!mealsBody) return;

    try {
      const res = await api.get(`/intake?date=${encodeURIComponent(dateStr)}`);
      if (!res.ok || !res.data.success) {
        mealsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:15px;">Could not load logged foods.</td></tr>`;
        return;
      }

      const intakes = res.data.data.intakes || [];
      let allEntries = [];
      intakes.forEach(doc => {
        (doc.entries || []).forEach(e => allEntries.push(e));
      });

      if (allEntries.length === 0) {
        mealsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:15px;">No foods logged for this date.</td></tr>`;
        return;
      }

      mealsBody.innerHTML = allEntries.map(e => {
        const qty = parseFloat(e.quantity_g || 100);
        const nutr = e.nutrients || {};
        const factor = qty / 100.0;
        const cal = Math.round((parseFloat(nutr.energy_kcal || 0) * factor) * 10) / 10;
        const prot = Math.round((parseFloat(nutr.protein_g || 0) * factor) * 10) / 10;

        return `
          <tr>
            <td><span class="badge badge-info" style="text-transform: capitalize;">${e.meal_type || 'meal'}</span></td>
            <td><strong>${e.food_name}</strong> <span style="font-size:0.75rem; color:#94a3b8;">(${e.food_code})</span></td>
            <td>${qty} g</td>
            <td><strong>${cal}</strong> kcal</td>
            <td><strong>${prot}</strong> g</td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error('Error loading dashboard meals:', e);
    }
  }

  loadDailySummary(targetDate);
});
