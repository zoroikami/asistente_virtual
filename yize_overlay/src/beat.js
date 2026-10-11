/**
 * beat.js — Detector de tempo y rastreador de compás rítmico (BPM & Phase).
 * Calcula el tempo musical a partir de frecuencias bajas (bajos/bombo)
 * y mantiene un oscilador suave de fase para sincronizar el baile de Yize.
 */

const damp = (c, t, l, dt) => c + (t - c) * (1 - Math.exp(-l * dt));

export class BeatTracker {
  constructor() {
    this.time = 0;
    this.avg = 0;
    this.lastBeat = -1;
    this.intervals = [];
    this.bpm = 0;
    this.phase = 0;   // 0..1, el beat principal cae en 0
    this.pulse = 0;   // 1 en el golpe, decae rápidamente
    this.level = 0;   // energía sonora general 0..1
  }

  get active() {
    return this.bpm > 0 && (this.time - this.lastBeat < 2.5);
  }

  update(dt, bass, total) {
    this.time += dt;
    this.avg = damp(this.avg, bass, 2, dt);
    this.level = damp(this.level, total, 3, dt);
    this.pulse = damp(this.pulse, 0, 10, dt);

    const onset = bass > this.avg * 1.35 + 0.05 && (this.time - this.lastBeat > 0.28);
    if (onset) {
      if (this.lastBeat > 0) {
        let iv = this.time - this.lastBeat;
        while (iv < 0.4) iv *= 2;          // pliega el tempo al rango 75–150 BPM
        while (iv > 0.8) iv /= 2;
        this.intervals.push(iv);
        if (this.intervals.length > 8) this.intervals.shift();
        const s = [...this.intervals].sort((a, b) => a - b);
        this.bpm = 60 / s[s.length >> 1];  // mediana de intervalos
      }
      this.lastBeat = this.time;
      this.pulse = 1;

      // Corrige la fase solo si el golpe cae cerca de lo esperado
      const err = this.phase > 0.5 ? this.phase - 1 : this.phase;
      if (Math.abs(err) < 0.25) this.phase -= err * 0.3;
    }

    if (this.bpm > 0) {
      this.phase = (this.phase + dt * (this.bpm / 60) + 1) % 1;
    }
    if (!this.active) {
      this.bpm = 0;
    }
  }

  reset() {
    this.bpm = 0;
    this.intervals = [];
    this.lastBeat = -1;
    this.phase = 0;
    this.pulse = 0;
    this.level = 0;
  }
}
