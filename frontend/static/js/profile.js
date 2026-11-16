/**
 * Profile Management Page Handler
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!api.requireAuth()) return;

  const profileForm = document.getElementById('profile-form');
  const alertBox = document.getElementById('profile-alert');
  const bmiDisplay = document.getElementById('bmi-display');
  const bmiCategoryBadge = document.getElementById('bmi-category-badge');

  function showAlert(msg, isError = true) {
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.className = `alert ${isError ? 'alert-danger' : 'alert-success'}`;
    alertBox.style.display = 'block';
  }

  function hideAlert() {
    if (!alertBox) return;
    alertBox.style.display = 'none';
  }

  function updateBMICard(bmi, category) {
    if (bmiDisplay) {
      bmiDisplay.textContent = bmi ? `${bmi} kg/m²` : '--';
    }
    if (bmiCategoryBadge) {
      bmiCategoryBadge.textContent = category || 'Not calculated';
      bmiCategoryBadge.className = 'badge';
      if (category === 'Normal weight') bmiCategoryBadge.classList.add('badge-success');
      else if (category === 'Underweight') bmiCategoryBadge.classList.add('badge-warning');
      else if (category === 'Overweight') bmiCategoryBadge.classList.add('badge-warning');
      else if (category === 'Obese') bmiCategoryBadge.classList.add('badge-danger');
      else bmiCategoryBadge.classList.add('badge-info');
    }
  }

  // Load existing profile
  const res = await api.get('/profile');
  if (res.ok && res.data.success) {
    const p = res.data.data.profile || {};
    if (p.age) document.getElementById('age').value = p.age;
    if (p.gender) document.getElementById('gender').value = p.gender;
    if (p.height_cm) document.getElementById('height_cm').value = p.height_cm;
    if (p.weight_kg) document.getElementById('weight_kg').value = p.weight_kg;
    if (p.activity_level) document.getElementById('activity_level').value = p.activity_level;
    if (p.diet_preference) document.getElementById('diet_preference').value = p.diet_preference;
    if (p.special_condition) document.getElementById('special_condition').value = p.special_condition;
    if (document.getElementById('ai_consent')) document.getElementById('ai_consent').checked = !!p.ai_consent;
    updateBMICard(p.bmi, p.bmi_category);
  }

  // Handle Profile Update
  if (profileForm) {
    profileForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert();

      const payload = {
        age: parseInt(document.getElementById('age').value),
        gender: document.getElementById('gender').value,
        height_cm: parseFloat(document.getElementById('height_cm').value),
        weight_kg: parseFloat(document.getElementById('weight_kg').value),
        activity_level: document.getElementById('activity_level').value,
        diet_preference: document.getElementById('diet_preference').value,
        special_condition: document.getElementById('special_condition').value,
        ai_consent: document.getElementById('ai_consent') ? document.getElementById('ai_consent').checked : false
      };

      const submitBtn = profileForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving Profile...';

      const updateRes = await api.put('/profile', payload);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save Profile';

      if (updateRes.ok && updateRes.data.success) {
        const updated = updateRes.data.data.profile;
        showAlert('Profile updated successfully! BMI and RDA cohorts refreshed.', false);
        updateBMICard(updated.bmi, updated.bmi_category);
        
        // Update user session in localStorage
        const user = api.getUser() || {};
        user.profile = updated;
        api.setUser(user);
      } else {
        showAlert(updateRes.data.message || 'Error updating profile.');
      }
    });
  }
});
