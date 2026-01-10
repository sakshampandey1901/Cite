export class TransparencyPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.citations = [];
    }

    setCitations(citations) {
        this.citations = citations;
        this.render();
    }

    clear() {
        this.citations = [];
        this.render();
    }

    render() {
        this.container.innerHTML = this.citations.map(cite => `
      <div class="citation-item">
        <div class="citation-type">${cite.type}</div>
        <div class="citation-source">${cite.source}</div>
        <div class="citation-loc">Page ${cite.page} • Score ${cite.score}%</div>
      </div>
    `).join('');
    }
}
