/**
 * modelSwitcher.js — Selector y cambiador de modelos/atuendos en caliente
 * Se abre con F3 o Ctrl+Shift+M.
 * Permite cambiar entre Yize VRM, modelos externos (.vrm) y el modo Live2D (VTube Studio).
 */

export class ModelSwitcher {
  constructor(onLoadVRM, onSwitchVTS) {
    this.onLoadVRM = onLoadVRM;
    this.onSwitchVTS = onSwitchVTS;
    this.isOpen = false;
    this._createDOM();
    this._bindKeys();
  }

  _createDOM() {
    this.container = document.createElement('div');
    this.container.id = 'model-switcher-modal';
    this.container.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(0.9);
      background: rgba(18, 12, 34, 0.95);
      border: 1px solid #b55fe6;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(181, 95, 230, 0.4);
      border-radius: 16px;
      padding: 20px 24px;
      z-index: 999999;
      color: #ffffff;
      font-family: 'Segoe UI', system-ui, sans-serif;
      width: 320px;
      opacity: 0;
      pointer-events: none;
      transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      -webkit-app-region: no-drag;
    `;

    this.container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <span style="font-weight:bold; font-size:15px; color:#f1f5f9;">🎭 Cambiar Avatar / Skin</span>
        <button id="close-switcher-btn" style="background:none; border:none; color:#94a3b8; font-size:18px; cursor:pointer;">✕</button>
      </div>
      <p style="font-size:12px; color:#cbd5e1; margin-bottom:14px; line-height:1.4;">
        Selecciona un modelo o sube un archivo <code>.vrm</code> nuevo sin reiniciar la aplicación:
      </p>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <button id="btn-avatar-default" style="
          background: rgba(181, 95, 230, 0.2);
          border: 1px solid #b55fe6;
          color: #fff;
          padding: 8px 12px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 13px;
          text-align: left;
        ">🌸 Yize VRM (Oficial 3D)</button>

        <button id="btn-avatar-vts" style="
          background: rgba(0, 243, 255, 0.15);
          border: 1px solid #00f3ff;
          color: #fff;
          padding: 8px 12px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 13px;
          text-align: left;
        ">🎭 Ruan Mei (Live2D / VTube Studio)</button>

        <label style="
          background: rgba(255, 255, 255, 0.08);
          border: 1px dashed #94a3b8;
          color: #e2e8f0;
          padding: 8px 12px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 13px;
          text-align: center;
          display: block;
          margin-top: 4px;
        ">
          📂 Cargar otro modelo .VRM...
          <input type="file" id="file-vrm-input" accept=".vrm" style="display:none;" />
        </label>
      </div>
      <div style="font-size:11px; color:#64748b; margin-top:12px; text-align:center;">
        Atajo: Presiona <b>F3</b> para abrir/cerrar este menú.
      </div>
    `;

    document.body.appendChild(this.container);

    this.container.querySelector('#close-switcher-btn').addEventListener('click', () => this.hide());
    this.container.querySelector('#btn-avatar-default').addEventListener('click', () => {
      const defaultUrl = new URL('./assets/Yize.vrm', window.location.href).href;
      this.onLoadVRM(defaultUrl, 'Yize.vrm');
      this.hide();
    });
    this.container.querySelector('#btn-avatar-vts').addEventListener('click', () => {
      this.onSwitchVTS();
      this.hide();
    });
    this.container.querySelector('#file-vrm-input').addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) {
        const url = URL.createObjectURL(file);
        this.onLoadVRM(url, file.name);
        this.hide();
      }
    });
  }

  _bindKeys() {
    window.addEventListener('keydown', (e) => {
      if (e.key === 'F3' || (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'm')) {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  toggle() {
    if (this.isOpen) this.hide();
    else this.show();
  }

  show() {
    this.isOpen = true;
    this.container.style.opacity = '1';
    this.container.style.transform = 'translate(-50%, -50%) scale(1)';
    this.container.style.pointerEvents = 'all';
  }

  hide() {
    this.isOpen = false;
    this.container.style.opacity = '0';
    this.container.style.transform = 'translate(-50%, -50%) scale(0.9)';
    this.container.style.pointerEvents = 'none';
  }
}
