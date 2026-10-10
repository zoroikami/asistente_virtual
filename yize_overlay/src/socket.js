/**
 * YizeSocket — WebSocket client que se reconecta automáticamente.
 * Se comunica con el bridge Python en ws://localhost:8765
 */
export class YizeSocket {
  constructor(url, callbacks = {}) {
    this.url = url;
    this.callbacks = callbacks;
    this.ws = null;
    this.reconnectDelay = 2000;
    this.connected = false;
    this._hasLoggedWaiting = false;
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.connected = true;
        this._hasLoggedWaiting = false;
        console.log('🔗 Conectado exitosamente con el backend Python (puerto 8765)');
        this.reconnectDelay = 2000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.callbacks.onMessage?.(data);
        } catch (e) {
          console.warn('Mensaje inválido:', event.data);
        }
      };

      this.ws.onclose = () => {
        const wasConnected = this.connected;
        this.connected = false;
        try { this.callbacks.onClose?.(); } catch (_) {}
        if (wasConnected) {
          console.log(`🔌 Conexión cerrada con Python. Reconectando en ${this.reconnectDelay}ms...`);
        } else if (!this._hasLoggedWaiting) {
          console.log('⏳ Esperando a que el backend de Python inicie...');
          this._hasLoggedWaiting = true;
        }
        setTimeout(() => this.connect(), this.reconnectDelay);
      };

      this.ws.onerror = () => {
        // Silencioso mientras espera que Python abra el puerto 8765
      };

    } catch (e) {
      setTimeout(() => this.connect(), this.reconnectDelay);
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this.ws?.close();
  }
}
