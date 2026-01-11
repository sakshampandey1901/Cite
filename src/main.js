import { KnowledgeBase } from './components/KnowledgeBase.js';
import { ModeSelector } from './components/ModeSelector.js';
import { OutputPanel } from './components/OutputPanel.js';
import { TransparencyPanel } from './components/TransparencyPanel.js';
import { AuthModal } from './components/AuthModal.js';
import { api } from './services/api.js';

class App {
  constructor() {
    this.authModal = new AuthModal();

    // Check authentication before initializing app
    if (!this.checkAuth()) {
      return; // Don't initialize app if not authenticated
    }

    // Expose UI if authenticated
    document.getElementById('app').style.display = 'grid';
    document.getElementById('btn-logout').style.display = 'block';

    this.kb = new KnowledgeBase('knowledge-base-list');
    this.modeSelector = new ModeSelector('mode-selector', (mode) => this.handleModeChange(mode));
    this.outputPanel = new OutputPanel('output-content');
    this.transparencyPanel = new TransparencyPanel('context-list');

    this.currentMode = null;
    this.editor = document.getElementById('editor');

    this.initActionArea();
    this.initUpload();
    this.initLogout();
  }

  checkAuth() {
    const token = api.getToken();
    if (!token) {
      // Show login modal
      this.authModal.show();
      return false;
    }
    return true;
  }

  initLogout() {
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        api.clearToken();
        window.location.reload();
      });
    }
  }

  handleModeChange(mode) {
    this.currentMode = mode;
    console.log("Mode selected:", mode);
    this.renderActionButton();
  }

  initActionArea() {
    this.actionArea = document.getElementById('action-area');
    this.renderActionButton();
  }

  initUpload() {
    const uploadBtn = document.getElementById('btn-upload');

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.txt,.md,.srt,.vtt';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    uploadBtn.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) {
        try {
          await this.kb.addFile(file);
        } catch (error) {
          alert(`Upload failed: ${error.message}`);
        }
      }
      fileInput.value = '';
    });
  }

  renderActionButton() {
    // If no mode selected, button is disabled or hidden?
    // "User must select exactly one mode before requesting assistance."

    const isDisabled = !this.currentMode;
    const btnText = isDisabled ? "Select Mode to Assist" : `Generate (${this.currentMode})`;

    this.actionArea.innerHTML = `
      <button class="btn-assist" id="btn-run-assist" ${isDisabled ? 'disabled' : ''}>
        <span>✨</span> ${btnText}
      </button>
    `;

    if (!isDisabled) {
      document.getElementById('btn-run-assist').addEventListener('click', () => this.runAssistant());
    }
  }

  async runAssistant() {
    if (!this.currentMode) return;

    const btn = document.getElementById('btn-run-assist');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span>⏳</span> Thinking...`;
    btn.disabled = true;

    try {
      const editorContent = this.editor.textContent || '';

      const response = await api.getAssistance({
        mode: this.currentMode,
        editor_content: editorContent,
        additional_context: null
      });

      this.outputPanel.addOutput({
        title: `${response.mode} Guidance`,
        text: response.guidance.replace(/\n/g, '<br>')
      });

      const citations = response.sources.map(source => ({
        type: source.rhetorical_role,
        source: source.source,
        page: source.page || source.timestamp || 'N/A',
        score: Math.round(source.similarity_score * 100)
      }));

      this.transparencyPanel.setCitations(citations);

    } catch (error) {
      console.error('Assistant failed:', error);
      this.outputPanel.addOutput({
        title: 'Error',
        text: `Failed to generate guidance: ${error.message}`
      });
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  }
}

// Boot
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
