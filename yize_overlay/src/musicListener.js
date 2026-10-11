/**
 * musicListener.js — Captura de audio loopback del sistema para detección de música.
 * Conecta el stream de audio de Windows a un AnalyserNode y alimenta a BeatTracker.
 */

import { BeatTracker } from './beat.js';

export class MusicListener {
  constructor(animator = null) {
    this.animator = animator;
    this.beat = new BeatTracker();
    this.ctx = null;
    this.analyser = null;
    this.freqData = null;
    this.stream = null;
    this.isListening = false;
    this._initPromise = null;
    this.noBeatTimer = 0;
  }

  setAnimator(animator) {
    this.animator = animator;
    if (this.animator) {
      this.animator.setBeatTracker(this.beat);
    }
  }

  async init() {
    if (this.isListening) return true;
    if (this._initPromise) return this._initPromise;

    this._initPromise = (async () => {
      try {
        if (!navigator.mediaDevices?.getDisplayMedia) {
          console.warn('[MusicListener] getDisplayMedia no está disponible en este entorno.');
          return false;
        }

        console.log('[MusicListener] Solicitando stream de audio loopback del sistema...');
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });

        // Detener inmediatamente las pistas de video: solo nos interesa el audio
        stream.getVideoTracks().forEach((track) => track.stop());

        const audioTracks = stream.getAudioTracks();
        if (!audioTracks || audioTracks.length === 0) {
          console.warn('[MusicListener] No se detectó pista de audio del sistema.');
          return false;
        }

        this.stream = stream;
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioCtx();

        if (this.ctx.state === 'suspended') {
          await this.ctx.resume();
        }

        this.analyser = this.ctx.createAnalyser();
        this.analyser.fftSize = 2048;
        this.analyser.smoothingTimeConstant = 0.3; // Bajo para capturar picos de transitorios/golpes

        const source = this.ctx.createMediaStreamSource(stream);
        source.connect(this.analyser);
        // IMPORTANTE: NO conectar a this.ctx.destination para evitar duplicar el sonido en altavoces

        this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
        this.isListening = true;

        if (this.animator) {
          this.animator.setBeatTracker(this.beat);
        }

        console.log('🎵 [MusicListener] Captura de audio del PC activa y enlazada con BeatTracker.');
        return true;
      } catch (err) {
        console.warn('[MusicListener] No se pudo iniciar captura de audio:', err);
        return false;
      } finally {
        this._initPromise = null;
      }
    })();

    return this._initPromise;
  }

  update(dt) {
    if (!this.isListening || !this.analyser) return;

    this.analyser.getByteFrequencyData(this.freqData);

    const sampleRate = this.ctx ? this.ctx.sampleRate : 48000;
    const binW = sampleRate / this.analyser.fftSize;
    const b0 = Math.round(40 / binW);
    const b1 = Math.round(150 / binW);

    let bass = 0;
    const maxB = Math.min(b1, this.freqData.length - 1);
    for (let i = b0; i <= maxB; i++) {
      bass += this.freqData[i];
    }
    const bassCount = Math.max(1, maxB - b0 + 1);
    bass /= (bassCount * 255);

    let total = 0;
    for (let i = 0; i < this.freqData.length; i++) {
      total += this.freqData[i];
    }
    total /= (this.freqData.length * 255);

    this.beat.update(dt, bass, total);

    // Auto-stop si pasan 5 segundos sin música / beat detectado mientras está en modo baile
    if (this.animator && this.animator.isDancing) {
      if (!this.beat.active) {
        this.noBeatTimer += dt;
        if (this.noBeatTimer > 5.0) {
          console.log('🎵 [MusicListener] 5s sin tempo detectado: regresando a pose natural.');
          this.animator.stopDancing();
          this.noBeatTimer = 0;
        }
      } else {
        this.noBeatTimer = 0;
      }
    }
  }

  stop() {
    this.isListening = false;
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.ctx) {
      try { this.ctx.close(); } catch (_) {}
      this.ctx = null;
    }
    this.analyser = null;
    this.beat.reset();
  }
}
