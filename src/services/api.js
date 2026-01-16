/**
 * API service for backend integration.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class APIError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.details = details;
  }
}

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = null;
  }

  /**
   * Set authentication token.
   * @param {string} token - JWT token
   */
  setToken(token) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  /**
   * Get authentication token.
   * @returns {string|null}
   */
  getToken() {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  /**
   * Clear authentication token.
   */
  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  /**
   * Make HTTP request with error handling and retries.
   * @param {string} endpoint - API endpoint
   * @param {object} options - Fetch options
   * @returns {Promise<any>}
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();

    const headers = {
      ...options.headers,
    };

    // Add auth header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Add Content-Type for JSON payloads
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    // Create timeout controller if AbortController is available
    let timeoutController = null;
    if (typeof AbortController !== 'undefined' && !options.signal) {
      timeoutController = new AbortController();
      setTimeout(() => {
        if (timeoutController) {
          timeoutController.abort();
        }
      }, 30000); // 30 second timeout
    }

    const config = {
      ...options,
      headers,
      signal: options.signal || (timeoutController ? timeoutController.signal : undefined),
    };

    try {
      const response = await fetch(url, config);

      // Handle non-2xx responses
      if (!response.ok) {
        let errorData = {};
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
          } else {
            errorData = { detail: `Server error: ${response.status} ${response.statusText}` };
          }
        } catch (parseError) {
          errorData = { detail: `Server error: ${response.status} ${response.statusText}` };
        }

        // Handle authentication errors (401 Unauthorized)
        if (response.status === 401) {
          this.clearToken();
          // Dispatch custom event for auth failure
          window.dispatchEvent(new CustomEvent('auth-failed', {
            detail: { message: 'Session expired. Please login again.' }
          }));
        }

        // Provide user-friendly error messages
        const errorMessage = errorData.detail || errorData.message || 
          (response.status === 503 ? 'Service temporarily unavailable. Please try again later.' :
           response.status === 500 ? 'Server error. Please try again or contact support.' :
           response.status === 404 ? 'Requested resource not found.' :
           response.status === 403 ? 'Access forbidden.' :
           `Request failed with status ${response.status}`);

        throw new APIError(errorMessage, response.status, errorData);
      }

      // Return JSON if content type is JSON
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }

      return response;
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      
      // Handle network errors with detailed messages
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        throw new APIError(
          'Request timed out. Please check your internet connection and try again.',
          0,
          { originalError: error.message, type: 'timeout' }
        );
      }
      
      if (error.message && (
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        error.message.includes('Network request failed')
      )) {
        throw new APIError(
          `Cannot connect to server. Please check:
1. Backend server is running (${this.baseURL})
2. Your internet connection
3. CORS settings if accessing from different domain`,
          0,
          { originalError: error.message, type: 'network' }
        );
      }
      
      // Generic error
      throw new APIError(
        `Network error: ${error.message || 'Unknown error'}. Please check your connection and try again.`,
        0,
        { originalError: error.message, type: 'unknown' }
      );
    }
  }

  /**
   * Upload a document.
   * @param {File} file - File to upload
   * @returns {Promise<object>}
   */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    return this.request('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  /**
   * Get list of user documents.
   * @returns {Promise<Array>}
   */
  async getDocuments() {
    return this.request('/documents', {
      method: 'GET',
    });
  }

  /**
   * Delete a document.
   * @param {string} documentId - Document ID
   * @returns {Promise<object>}
   */
  async deleteDocument(documentId) {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Request assistance from the AI.
   * @param {object} params - Request parameters
   * @param {string} params.mode - Task mode (START, CONTINUE, REFRAME, etc.)
   * @param {string} params.editor_content - Current editor content
   * @param {string} [params.additional_context] - Optional additional context
   * @returns {Promise<object>}
   */
  async getAssistance({ mode, editor_content, additional_context }) {
    return this.request('/assist', {
      method: 'POST',
      body: JSON.stringify({
        mode: mode.toUpperCase().replace(' ', '_'),
        editor_content: editor_content || '',
        additional_context: additional_context || null,
      }),
    });
  }

  /**
   * Health check.
   * @returns {Promise<object>}
   */
  async healthCheck() {
    return this.request('/health', {
      method: 'GET',
    });
  }
}

export const api = new APIService();
export { APIError };
