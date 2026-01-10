export class ModeSelector {
    constructor(containerId, onModeChange) {
        this.container = document.getElementById(containerId);
        this.onModeChange = onModeChange;
        this.modes = ["Start", "Continue", "Reframe", "Stuck Diagnosis", "Outline"];
        this.activeMode = null;
        this.render();
    }

    selectMode(mode) {
        this.activeMode = mode;
        this.render();
        this.onModeChange(mode);
    }

    render() {
        this.container.innerHTML = this.modes.map(mode => `
      <button 
        class="mode-btn ${this.activeMode === mode ? 'active' : ''}" 
        data-mode="${mode}"
      >
        ${mode}
      </button>
    `).join('');

        // Re-attach listeners
        this.container.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => this.selectMode(btn.dataset.mode));
        });
    }
}
