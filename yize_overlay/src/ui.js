/**
 * YizeUI — Modo 100% limpio (sin burbujas flotantes ni emojis).
 * Solo el avatar 3D se renderiza en la pantalla.
 */
export const YizeUI = {
  showBubble(text, emotion = null) {
    // Modo limpio: no mostrar texto flotante sobre la cabeza
  },

  hideBubble() {
    // No-op
  },

  setStatus(text, isTalking = false) {
    // No-op
  },

  showEmotion(emotion) {
    // Modo limpio: no mostrar emojis flotantes
  },

  setPrivacy(mode = 'idle') {
    const dot = document.getElementById('privacy-dot');
    const label = document.getElementById('privacy-label');
    const pill = document.getElementById('privacy-pill');
    if (!dot || !label) return;

    dot.className = `privacy-dot ${mode}`;
    const labels = {
      idle: 'Standby',
      mic: 'Mic activo',
      cam: 'Cámara en RAM',
      vision: 'Escaneando',
      muted: 'Silenciado'
    };
    label.textContent = labels[mode] || 'Protegido';

    const tooltips = {
      idle: 'Privacidad: Sensores inactivos y protegidos',
      mic: 'Privacidad: Micrófono escuchando tu voz',
      cam: 'Privacidad: Cámara procesando gestos 100% en local en RAM',
      vision: 'Privacidad: Escaneando elemento en pantalla',
      muted: 'Privacidad: Modo Sigilo Total activo'
    };
    if (pill) pill.title = tooltips[mode] || 'Privacidad';
  }
};
