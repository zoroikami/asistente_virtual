/**
 * VoicePlayer: reproduce en el frontend el audio que manda el backend y
 * conecta el AnalyserNode al animador para el lip-sync por volumen real.
 *
 * Uso (socket.js):
 *   const voice = new VoicePlayer(animator);
 *   voice.onEnded = () => ws.send(JSON.stringify({ type: 'audio_done' }));
 *   ws.onmessage = (ev) => {
 *     const msg = JSON.parse(ev.data);
 *     if (msg.type === 'audio') voice.play(msg.data);   // base64
 *     if (msg.type === 'audio_stop') voice.stop();
 *   };
 */
export class VoicePlayer {
  constructor(animator) {
    this.animator = animator;
    this.ctx = new AudioContext();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.3;
    this.analyser.connect(this.ctx.destination);
    if (this.animator && typeof this.animator.setAnalyser === 'function') {
      this.animator.setAnalyser(this.analyser);
    }
    this.current = null;
    this.onEnded = null;
  }

  setAnimator(animator) {
    this.animator = animator;
    if (this.animator && typeof this.animator.setAnalyser === 'function') {
      this.animator.setAnalyser(this.analyser);
    }
  }

  async play(base64) {
    if (this.ctx.state === 'suspended') await this.ctx.resume();

    const bin = atob(base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const buffer = await this.ctx.decodeAudioData(bytes.buffer);

    this.stop();

    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(this.analyser);
    src.onended = () => {
      if (this.current !== src) return;
      this.current = null;
      if (this.animator) this.animator.stopTalking();
      if (this.onEnded) this.onEnded();
    };

    this.current = src;
    if (this.animator) this.animator.startTalking();
    src.start();
  }

  stop() {
    if (!this.current) return;
    const src = this.current;
    this.current = null;
    src.onended = null;
    try { src.stop(); } catch (_) {}
    if (this.animator) this.animator.stopTalking();
  }
}
