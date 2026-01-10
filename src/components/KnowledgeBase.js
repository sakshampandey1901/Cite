import { api } from '../services/api.js';

export class KnowledgeBase {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.files = [];
    this.loadDocuments();
  }

  async loadDocuments() {
    try {
      const documents = await api.getDocuments();
      this.files = documents.map(doc => ({
        id: doc.id,
        title: doc.title,
        type: doc.content_type,
        date: new Date(doc.created_at).toISOString().split('T')[0],
        status: doc.status
      }));
      this.render();
    } catch (error) {
      console.error('Failed to load documents:', error);
      this.files = [];
      this.render();
    }
  }

  async addFile(file) {
    const tempId = Date.now();
    this.files.push({
      id: tempId,
      title: file.name,
      type: file.type || 'unknown',
      date: new Date().toISOString().split('T')[0],
      status: "uploading"
    });
    this.render();

    try {
      const result = await api.uploadDocument(file);

      const index = this.files.findIndex(f => f.id === tempId);
      if (index !== -1) {
        this.files[index] = {
          id: result.document_id,
          title: result.filename,
          type: result.content_type || 'unknown',
          date: new Date(result.created_at).toISOString().split('T')[0],
          status: result.status
        };
        this.render();
      }
    } catch (error) {
      console.error('Upload failed:', error);
      const index = this.files.findIndex(f => f.id === tempId);
      if (index !== -1) {
        this.files[index].status = "failed";
        this.render();
      }
      throw error;
    }
  }

  render() {
    this.container.innerHTML = this.files.map(file => `
      <div class="file-item">
        <div class="file-title">${file.title}</div>
        <div class="file-meta">
          <span>${file.type}</span>
          <span>${file.date}</span>
        </div>
        <div class="file-status ${file.status}">${file.status}</div>
      </div>
    `).join('');
  }
}
