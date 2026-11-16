/**
 * Centralized API & Authentication Client for NutriScan
 * Handles Bearer token persistence, 401 redirects, and JSON network requests.
 */

const API_BASE = '/api';

const api = {
  getToken() {
    return localStorage.getItem('nutriscan_token');
  },

  setToken(token) {
    localStorage.setItem('nutriscan_token', token);
  },

  getUser() {
    try {
      const u = localStorage.getItem('nutriscan_user');
      return u ? JSON.parse(u) : null;
    } catch (e) {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem('nutriscan_user', JSON.stringify(user));
  },

  isLoggedIn() {
    return Boolean(this.getToken());
  },

  logout() {
    localStorage.removeItem('nutriscan_token');
    localStorage.removeItem('nutriscan_user');
    window.location.href = '/login';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/login';
      return false;
    }
    return true;
  },

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401) {
        // Clear expired credentials and redirect to login
        localStorage.removeItem('nutriscan_token');
        localStorage.removeItem('nutriscan_user');
        if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
          window.location.href = '/login';
        }
      }

      const data = await response.json().catch(() => ({
        success: false,
        message: 'Non-JSON server response',
        data: null
      }));

      return {
        ok: response.ok,
        status: response.status,
        data
      };
    } catch (err) {
      console.error('[API Network Error]', err);
      return {
        ok: false,
        status: 0,
        data: {
          success: false,
          message: 'Unable to connect to the NutriScan server. Please verify network.',
          data: null
        }
      };
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};

window.api = api;
