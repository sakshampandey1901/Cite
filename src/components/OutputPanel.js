export class OutputPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.outputs = [];
    }

    addOutput(data) {
        this.outputs.unshift(data); // Newest first
        this.render();
    }

    render() {
        this.container.innerHTML = this.outputs.map(out => `
      <div class="output-block">
        <div class="output-header">${out.title || "Assistant Suggestion"}</div>
        <div class="output-body">${out.text}</div>
        <div class="output-actions">
          <button class="btn-copy">Copy to Editor</button>
        </div>
      </div>
    `).join('');

        // Wire up copy buttons (simplistic implementation)
        this.container.querySelectorAll('.btn-copy').forEach((btn, idx) => {
            btn.addEventListener('click', () => {
                navigator.clipboard.writeText(this.outputs[idx].text);
                btn.textContent = "Copied!";
                setTimeout(() => btn.textContent = "Copy to Editor", 1500);
            });
        });
    }
}
