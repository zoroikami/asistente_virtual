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
};
