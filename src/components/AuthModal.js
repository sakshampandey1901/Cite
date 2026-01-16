import { api } from '../services/api.js';

export class AuthModal {
  constructor() {
    this.isVisible = false;
    this.mode = 'login'; // 'login' or 'signup'
    this.render();
    this.attachEvents();
  }

  render() {
    const modalHTML = `
      <div id="auth-modal" class="auth-modal" style="display: none;">
        <div class="auth-modal-content">
          <span class="auth-close">&times;</span>
          <h2 id="auth-title">Login</h2>
          <form id="auth-form">
            <input type="email" id="auth-email" placeholder="Email" required />
            <input type="password" id="auth-password" placeholder="Password (min 8 characters)" required />
            <button type="submit" id="auth-submit">Login</button>
            <p id="auth-toggle">
              Don't have an account? <a href="#" id="auth-switch">Sign up</a>
            </p>
            <div id="auth-error" class="auth-error" style="display: none;"></div>
          </form>
        </div>
      </div>
    `;

    if (!document.getElementById('auth-modal')) {
      document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
  }

  attachEvents() {
    const modal = document.getElementById('auth-modal');
    const closeBtn = document.querySelector('.auth-close');
    const form = document.getElementById('auth-form');
    const switchLink = document.getElementById('auth-switch');

    closeBtn.onclick = () => this.hide();
    window.onclick = (e) => {
      if (e.target === modal) this.hide();
    };

    switchLink.onclick = (e) => {
      e.preventDefault();
      this.toggleMode();
    };

    form.onsubmit = async (e) => {
      e.preventDefault();
      await this.handleSubmit();
    };
  }

  toggleMode() {
    this.mode = this.mode === 'login' ? 'signup' : 'login';
    const title = document.getElementById('auth-title');
    const submitBtn = document.getElementById('auth-submit');
    const toggleText = document.getElementById('auth-toggle');
    const switchLink = document.getElementById('auth-switch');

    if (this.mode === 'signup') {
      title.textContent = 'Sign Up';
      submitBtn.textContent = 'Sign Up';
      toggleText.childNodes[0].textContent = 'Already have an account? ';
      switchLink.textContent = 'Login';
    } else {
      title.textContent = 'Login';
      submitBtn.textContent = 'Login';
      toggleText.childNodes[0].textContent = "Don't have an account? ";
      switchLink.textContent = 'Sign up';
    }
    this.hideError();
  }

  async handleSubmit() {
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    const submitBtn = document.getElementById('auth-submit');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    this.hideError();

    try {
      let response;
      if (this.mode === 'signup') {
        response = await this.signup(email, password);
      } else {
        response = await this.login(email, password);
      }

      // Store token
      api.setToken(response.access_token);

      // Close modal and reload
      this.hide();
      window.location.reload();

    } catch (error) {
      // Extract user-friendly error message
      let errorMessage = 'Authentication failed';
      
      if (error.message) {
        errorMessage = error.message;
      } else if (error.details && error.details.detail) {
        errorMessage = error.details.detail;
      } else if (error.details && typeof error.details === 'string') {
        errorMessage = error.details;
      }
      
      // Show error to user
      this.showError(errorMessage);
      submitBtn.disabled = false;
      submitBtn.textContent = this.mode === 'login' ? 'Login' : 'Sign Up';
      
      // Log full error for debugging
      console.error('Authentication error:', error);
    }
  }

  async signup(email, password) {
    return api.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  }

  async login(email, password) {
    return api.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  }

  show() {
    this.isVisible = true;
    document.getElementById('auth-modal').style.display = 'flex';
  }

  hide() {
    this.isVisible = false;
    document.getElementById('auth-modal').style.display = 'none';
    document.getElementById('auth-form').reset();
    this.hideError();
  }

  showError(message) {
    const errorDiv = document.getElementById('auth-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
  }

  hideError() {
    const errorDiv = document.getElementById('auth-error');
    errorDiv.style.display = 'none';
  }
}