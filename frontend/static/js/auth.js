/**
 * Authentication Form Handlers (Login & Register)
 */

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const alertBox = document.getElementById('auth-alert');

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

  // Handle Login
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert();

      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!email || !password) {
        showAlert('Please enter both email and password.');
        return;
      }

      const submitBtn = loginForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Signing in...';

      const res = await api.post('/auth/login', { email, password });
      submitBtn.disabled = false;
      submitBtn.textContent = 'Sign In';

      if (res.ok && res.data.success) {
        api.setToken(res.data.data.token);
        api.setUser(res.data.data.user);
        showAlert('Login successful! Redirecting...', false);
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 500);
      } else {
        showAlert(res.data.message || 'Invalid email or password.');
      }
    });
  }

  // Handle Registration
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert();

      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!name || name.length < 2) {
        showAlert('Please provide your full name (at least 2 characters).');
        return;
      }
      if (!email || !email.includes('@')) {
        showAlert('Please provide a valid email address.');
        return;
      }
      if (!password || password.length < 8) {
        showAlert('Password must be at least 8 characters long.');
        return;
      }

      const submitBtn = registerForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating account...';

      const res = await api.post('/auth/register', { name, email, password });
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Account';

      if (res.ok && res.data.success) {
        api.setToken(res.data.data.token);
        api.setUser(res.data.data.user);
        showAlert('Account created! Redirecting to complete your profile...', false);
        setTimeout(() => {
          window.location.href = '/profile';
        }, 600);
      } else {
        showAlert(res.data.message || 'Registration failed. Try again.');
      }
    });
  }
});
