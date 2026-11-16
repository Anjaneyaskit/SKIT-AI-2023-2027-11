/**
 * Daily Dietary Intake Logging Handler with Natural Language Meal Parsing
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!api.requireAuth()) return;

  const searchInput = document.getElementById('food-search');
  const searchResults = document.getElementById('search-results');
  const selectedFoodCode = document.getElementById('selected-food-code');
  const selectedFoodName = document.getElementById('selected-food-name');
  const selectedFoodBadge = document.getElementById('selected-food-badge');
  const quantityInput = document.getElementById('food-quantity');
  const mealTypeSelect = document.getElementById('meal-type');
  const freqInput = document.getElementById('frequency-week');
  const addBtn = document.getElementById('add-item-btn');
  const entriesTableBody = document.getElementById('intake-entries-body');
  const submitIntakeBtn = document.getElementById('submit-intake-btn');
  const intakeDateInput = document.getElementById('intake-date');
  const alertBox = document.getElementById('intake-alert');

  // NLP Elements
  const nlpInput = document.getElementById('nlp-meal-input');
  const parseMealBtn = document.getElementById('parse-meal-btn');
  const nlpResultsBox = document.getElementById('nlp-results-box');
  const nlpItemsList = document.getElementById('nlp-items-list');
  const addParsedBtn = document.getElementById('add-parsed-items-btn');

  let stagedEntries = [];
  let parsedCandidates = [];
  let debounceTimeout = null;

  // Set today's date by default
  const today = new Date().toISOString().split('T')[0];
  if (intakeDateInput) intakeDateInput.value = today;

  function showAlert(msg, isError = true) {
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.className = `alert ${isError ? 'alert-danger' : 'alert-success'}`;
    alertBox.style.display = 'block';
    alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideAlert() {
    if (!alertBox) return;
    alertBox.style.display = 'none';
  }

  // --- Natural Language Meal Parsing (Feature N1) ---
  if (parseMealBtn) {
    parseMealBtn.addEventListener('click', async () => {
      hideAlert();
      const text = nlpInput.value.trim();
      if (!text) {
        showAlert('Please enter a meal description first.');
        return;
      }

      parseMealBtn.disabled = true;
      parseMealBtn.textContent = 'Analyzing Meal...';

      try {
        const res = await api.post('/history/nlp/parse-meal', { text });
        parseMealBtn.disabled = false;
        parseMealBtn.textContent = '⚡ Parse Meal';

        if (res.ok && res.data.success) {
          parsedCandidates = res.data.data.matched_items || [];
          if (parsedCandidates.length === 0) {
            showAlert('Could not reliably match any IFCT Indian foods from that description. Please try standard food terms or search manually below.');
            nlpResultsBox.style.display = 'none';
          } else {
            renderParsedCandidates(parsedCandidates);
            nlpResultsBox.style.display = 'block';
          }
        } else {
          showAlert(res.data.message || 'Error analyzing meal text.');
        }
      } catch (err) {
        parseMealBtn.disabled = false;
        parseMealBtn.textContent = '⚡ Parse Meal';
        showAlert('Network error while parsing meal description.');
      }
    });
  }

  function renderParsedCandidates(items) {
    nlpItemsList.innerHTML = items.map((item, idx) => {
      const code = item.food_code || item.matched_food_code || 'AI_CUSTOM';
      const name = item.food_name || item.matched_food_name || 'Food Item';
      const qty = item.quantity_g || item.estimated_grams || 100;
      const meal = item.meal_type || 'breakfast';
      const phrase = item.original_phrase || item.input_text || name;
      const isAi = item.is_ai_generated || (code && code.startsWith('AI_'));

      const confScore = Math.round((item.confidence || (item.match_confidence_pct ? item.match_confidence_pct / 100 : 0.8)) * 100);
      const confBadge = isAi
        ? `<span class="badge" style="background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; font-size: 0.75rem;">✨ AI Estimated Recipe</span>`
        : (confScore >= 80 
            ? `<span class="badge badge-success" style="font-size: 0.75rem;">${confScore}% Match</span>`
            : `<span class="badge badge-warning" style="font-size: 0.75rem;">Review Match (${confScore}%)</span>`);

      return `
        <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; padding:0.6rem 0.8rem; border-radius:6px; border:1px solid #e2e8f0; gap:0.5rem; flex-wrap:wrap;">
          <div>
            <strong>${name}</strong>
            <span style="font-size:0.78rem; color:#64748b;">(Code: ${code})</span>
            <div style="font-size:0.78rem; color:#64748b;">Detected query: <em>"${phrase}"</em> &bull; <strong style="text-transform: capitalize; color: var(--primary-dark);">${meal}</strong></div>
          </div>
          <div style="display:flex; align-items:center; gap:0.6rem;">
            ${confBadge}
            <div style="display:flex; align-items:center; gap:0.25rem;">
              <input type="number" id="parsed-qty-${idx}" value="${qty}" min="5" max="2000" step="5" style="width:75px; padding:0.3rem; border:1px solid #cbd5e1; border-radius:4px; font-size:0.85rem;">
              <span style="font-size:0.8rem; color:#64748b;">g</span>
            </div>
            <button type="button" class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="removeParsedCandidate(${idx})">✕</button>
          </div>
        </div>
      `;
    }).join('');
  }

  window.removeParsedCandidate = (idx) => {
    parsedCandidates.splice(idx, 1);
    if (parsedCandidates.length === 0) {
      nlpResultsBox.style.display = 'none';
    } else {
      renderParsedCandidates(parsedCandidates);
    }
  };

  if (addParsedBtn) {
    addParsedBtn.addEventListener('click', () => {
      if (parsedCandidates.length === 0) return;

      parsedCandidates.forEach((item, idx) => {
        const qtyEl = document.getElementById(`parsed-qty-${idx}`);
        const code = item.food_code || item.matched_food_code || 'AI_CUSTOM';
        const name = item.food_name || item.matched_food_name || 'Food Item';
        const defaultQty = item.quantity_g || item.estimated_grams || 100;
        const finalQty = qtyEl ? parseFloat(qtyEl.value || defaultQty) : defaultQty;
        const meal = item.meal_type || 'breakfast';

        stagedEntries.push({
          food_code: code,
          food_name: name,
          quantity_g: finalQty,
          meal_type: meal,
          frequency_per_week: 7
        });
      });

      parsedCandidates = [];
      nlpResultsBox.style.display = 'none';
      if (nlpInput) nlpInput.value = '';
      renderStagedTable();
      showAlert('Added parsed items to staged log! Review and save below.', false);
    });
  }

  // --- Manual Debounced Food Search ---
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimeout);
      const query = e.target.value.trim();
      if (query.length < 2) {
        searchResults.style.display = 'none';
        searchResults.innerHTML = '';
        return;
      }

      debounceTimeout = setTimeout(async () => {
        const res = await api.get(`/foods?q=${encodeURIComponent(query)}&limit=15`);
        if (res.ok && res.data.success) {
          const foods = res.data.data.foods;
          if (foods.length === 0) {
            searchResults.innerHTML = `<div style="padding:10px; color:#64748b; font-size:0.9rem;">No Indian foods matched "${query}".</div>`;
          } else {
            searchResults.innerHTML = foods.map(f => `
              <div class="search-item" data-code="${f.code}" data-name="${f.name}">
                <div>
                  <strong>${f.name}</strong>
                  <div class="search-item-meta">Code: ${f.code} | Region: ${f.region || 'All'}</div>
                </div>
                <div class="search-item-meta" style="text-align:right;">
                  ${f.headline_nutrients.energy_kcal} kcal | ${f.headline_nutrients.protein_g}g Protein
                </div>
              </div>
            `).join('');

            // Click listener on search items
            searchResults.querySelectorAll('.search-item').forEach(item => {
              item.addEventListener('click', () => {
                const code = item.getAttribute('data-code');
                const name = item.getAttribute('data-name');
                selectedFoodCode.value = code;
                selectedFoodName.value = name;
                if (selectedFoodBadge) {
                  selectedFoodBadge.textContent = `${name} (${code})`;
                  selectedFoodBadge.style.display = 'inline-block';
                }
                searchInput.value = '';
                searchResults.style.display = 'none';
              });
            });
          }
          searchResults.style.display = 'block';
        }
      }, 300);
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = 'none';
      }
    });
  }

  // Add Single Item Manually
  if (addBtn) {
    addBtn.addEventListener('click', () => {
      hideAlert();
      const code = selectedFoodCode.value;
      const name = selectedFoodName.value;
      const qty = parseFloat(quantityInput.value);
      const meal = mealTypeSelect.value;
      const freq = freqInput ? parseFloat(freqInput.value || 7) : 7;

      if (!code || !name) {
        showAlert('Please search and select a food item first.');
        return;
      }
      if (!qty || qty <= 0) {
        showAlert('Please enter a valid portion in grams (> 0).');
        return;
      }

      stagedEntries.push({
        food_code: code,
        food_name: name,
        quantity_g: qty,
        meal_type: meal,
        frequency_per_week: freq
      });

      selectedFoodCode.value = '';
      selectedFoodName.value = '';
      if (selectedFoodBadge) selectedFoodBadge.style.display = 'none';
      quantityInput.value = '100';
      if (freqInput) freqInput.value = '7';

      renderStagedTable();
    });
  }

  function renderStagedTable() {
    if (!entriesTableBody) return;
    if (stagedEntries.length === 0) {
      entriesTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:20px;">No foods added yet. Search or use the AI meal box above.</td></tr>`;
      if (submitIntakeBtn) submitIntakeBtn.disabled = true;
      return;
    }

    entriesTableBody.innerHTML = stagedEntries.map((item, idx) => `
      <tr>
        <td><strong>${item.food_name}</strong> <span style="font-size:0.75rem; color:#94a3b8;">(${item.food_code})</span></td>
        <td><span class="badge badge-info">${item.meal_type}</span></td>
        <td>${item.quantity_g} g</td>
        <td><span class="badge badge-success">Daily</span></td>
        <td>
          <button class="btn btn-danger" style="padding:0.3rem 0.6rem; font-size:0.8rem;" onclick="removeEntry(${idx})">Remove</button>
        </td>
      </tr>
    `).join('');

    if (submitIntakeBtn) submitIntakeBtn.disabled = false;
  }

  window.removeEntry = (index) => {
    stagedEntries.splice(index, 1);
    renderStagedTable();
  };

  // Saved Meals Management
  const savedMealsBody = document.getElementById('saved-meals-body');
  const savedCountBadge = document.getElementById('saved-meals-count-badge');
  const savedDateLabel = document.getElementById('saved-meals-date-label');
  const savedLoading = document.getElementById('saved-meals-loading');
  const savedDayTotals = document.getElementById('saved-day-totals');
  const refreshSavedBtn = document.getElementById('refresh-saved-btn');

  async function loadSavedMeals(targetDate) {
    if (!savedMealsBody) return;
    const dateStr = targetDate || (intakeDateInput ? intakeDateInput.value : today);
    if (savedDateLabel) savedDateLabel.textContent = `Date: ${dateStr} (saved in database)`;
    if (savedLoading) savedLoading.style.display = 'block';

    try {
      const res = await api.get(`/intake?date=${encodeURIComponent(dateStr)}`);
      if (savedLoading) savedLoading.style.display = 'none';

      if (!res.ok || !res.data.success) {
        savedMealsBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:20px;">Could not load saved meals.</td></tr>`;
        return;
      }

      const intakes = res.data.data.intakes || [];
      let allEntries = [];
      intakes.forEach(doc => {
        (doc.entries || []).forEach((e, idx) => {
          allEntries.push({
            ...e,
            intake_id: doc._id,
            entry_idx: idx
          });
        });
      });

      if (savedCountBadge) savedCountBadge.textContent = `${allEntries.length} Items`;

      if (allEntries.length === 0) {
        savedMealsBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94a3b8; padding:25px;">No meals saved yet for this date (${dateStr}). Add foods above and click "Save & Proceed".</td></tr>`;
        if (savedDayTotals) savedDayTotals.style.display = 'none';
        return;
      }

      let totalCal = 0, totalProt = 0, totalCarbs = 0, totalFat = 0;

      savedMealsBody.innerHTML = allEntries.map(e => {
        const qty = parseFloat(e.quantity_g || 100);
        const nutr = e.nutrients || {};
        const factor = qty / 100.0;
        const cal = Math.round((parseFloat(nutr.energy_kcal || 0) * factor) * 10) / 10;
        const prot = Math.round((parseFloat(nutr.protein_g || 0) * factor) * 10) / 10;
        const carbs = Math.round((parseFloat(nutr.carbs_g || 0) * factor) * 10) / 10;
        const fat = Math.round((parseFloat(nutr.fat_g || 0) * factor) * 10) / 10;

        totalCal += cal;
        totalProt += prot;
        totalCarbs += carbs;
        totalFat += fat;

        return `
          <tr>
            <td><span class="badge badge-info" style="text-transform: capitalize;">${e.meal_type || 'meal'}</span></td>
            <td><strong>${e.food_name}</strong> <span style="font-size:0.75rem; color:#94a3b8; display:block;">${e.food_code}</span></td>
            <td>${qty} g</td>
            <td><strong>${cal}</strong> kcal</td>
            <td><strong>${prot}</strong> g</td>
            <td>
              <button class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#ef4444; border-color:#fca5a5;" onclick="deleteSavedEntry('${e.intake_id}', ${e.entry_idx})">
                ✕ Delete
              </button>
            </td>
          </tr>
        `;
      }).join('');

      // Update Day Totals Bar
      if (savedDayTotals) {
        savedDayTotals.style.display = 'block';
        const calEl = document.getElementById('day-total-cal');
        const protEl = document.getElementById('day-total-prot');
        const carbsEl = document.getElementById('day-total-carbs');
        const fatEl = document.getElementById('day-total-fat');
        if (calEl) calEl.textContent = `${Math.round(totalCal * 10) / 10} kcal`;
        if (protEl) protEl.textContent = `${Math.round(totalProt * 10) / 10} g`;
        if (carbsEl) carbsEl.textContent = `${Math.round(totalCarbs * 10) / 10} g`;
        if (fatEl) fatEl.textContent = `${Math.round(totalFat * 10) / 10} g`;
      }
    } catch (err) {
      if (savedLoading) savedLoading.style.display = 'none';
      console.error('Error loading saved meals:', err);
    }
  }

  window.deleteSavedEntry = async (intakeId, entryIdx) => {
    if (!confirm('Are you sure you want to remove this logged food entry?')) return;
    try {
      const res = await api.delete(`/intake/${intakeId}/entry/${entryIdx}`);
      if (res.ok) {
        showAlert('Food entry removed from database.', false);
        loadSavedMeals(intakeDateInput ? intakeDateInput.value : today);
      } else {
        showAlert(res.data.message || 'Failed to remove entry.');
      }
    } catch (e) {
      showAlert('Network error while removing entry.');
    }
  };

  if (refreshSavedBtn) {
    refreshSavedBtn.addEventListener('click', () => {
      loadSavedMeals(intakeDateInput ? intakeDateInput.value : today);
    });
  }

  if (intakeDateInput) {
    intakeDateInput.addEventListener('change', () => {
      loadSavedMeals(intakeDateInput.value);
    });
  }

  // Submit Intake Log
  if (submitIntakeBtn) {
    submitIntakeBtn.addEventListener('click', async () => {
      hideAlert();
      if (stagedEntries.length === 0) {
        showAlert('Please add at least one food item before submitting.');
        return;
      }

      submitIntakeBtn.disabled = true;
      submitIntakeBtn.textContent = 'Saving Intake Log...';

      const targetDate = intakeDateInput ? intakeDateInput.value : today;
      const payload = {
        date: targetDate,
        entries: stagedEntries
      };

      const res = await api.post('/intake', payload);
      submitIntakeBtn.disabled = false;
      submitIntakeBtn.textContent = 'Save & Proceed to Assessment';

      if (res.ok && res.data.success) {
        stagedEntries = [];
        renderStagedTable();
        await loadSavedMeals(targetDate);
        showAlert(`Successfully saved meal entries to database for ${targetDate}! You can now proceed to the Symptom Questionnaire or view your Assessment.`, false);
      } else {
        showAlert(res.data.message || 'Error saving intake log.');
      }
    });
  }

  renderStagedTable();
  loadSavedMeals(today);
});
