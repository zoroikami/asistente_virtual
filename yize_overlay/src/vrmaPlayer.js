/**
 * vrmaPlayer.js — Reproductor de Animaciones VRMA (@pixiv/three-vrm-animation)
 * Permite cargar clips .vrma profesionales (de Mixamo, Booth o VRoid),
 * mezclarlos con AnimationMixer y transicionar suavemente con las poses procedurales.
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';

export class VRMAPlayer {
  constructor(vrm) {
    this.vrm = vrm;
    this.mixer = new THREE.AnimationMixer(vrm.scene);
    this.loader = new GLTFLoader();
    this.loader.register((parser) => new VRMAnimationLoaderPlugin(parser));

    this.clips = new Map();         // name -> AnimationClip
    this.currentAction = null;
    this.isPlaying = false;
    this.onAnimationFinished = null;

    this.mixer.addEventListener('finished', (e) => {
      this.isPlaying = false;
      if (this.onAnimationFinished) {
        this.onAnimationFinished(e.action.getClip().name);
      }
    });
  }

  setVRM(newVRM) {
    this.vrm = newVRM;
    if (this.mixer) this.mixer.stopAllAction();
    this.mixer = new THREE.AnimationMixer(newVRM.scene);
    this.clips.clear();
    this.currentAction = null;
    this.isPlaying = false;
  }

  /**
   * Carga un archivo .vrma desde una URL o ruta local.
   */
  async loadVRMA(name, url) {
    return new Promise((resolve, reject) => {
      this.loader.load(
        url,
        (gltf) => {
          const vrmAnim = gltf.userData.vrmAnimation;
          if (!vrmAnim) {
            reject(new Error(`El archivo ${url} no contiene datos de vrmAnimation válidos.`));
            return;
          }
          const clip = createVRMAnimationClip(vrmAnim, this.vrm);
          clip.name = name;
          this.clips.set(name, clip);
          console.log(`🎬 [VRMA] Animación '${name}' cargada exitosamente.`);
          resolve(clip);
        },
        undefined,
        (err) => {
          console.warn(`[VRMA] No se pudo cargar '${name}' desde ${url}:`, err);
          reject(err);
        }
      );
    });
  }

  /**
   * Reproduce una animación cargada con crossfade suave.
   */
  play(name, options = {}) {
    const clip = this.clips.get(name);
    if (!clip) {
      console.warn(`[VRMA] Clip '${name}' no encontrado.`);
      return false;
    }

    const {
      loop = false,
      crossFade = 0.4,
      clampWhenFinished = true,
      timeScale = 1.0,
      onFinished = null,
    } = options;

    this.onAnimationFinished = onFinished;
    const nextAction = this.mixer.clipAction(clip);
    nextAction.reset();
    nextAction.timeScale = timeScale;
    nextAction.clampWhenFinished = clampWhenFinished;
    nextAction.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);

    if (this.currentAction && this.currentAction !== nextAction) {
      nextAction.crossFadeFrom(this.currentAction, crossFade, true);
    }
    nextAction.play();
    this.currentAction = nextAction;
    this.isPlaying = true;
    return true;
  }

  stop(crossFade = 0.3) {
    if (this.currentAction) {
      this.currentAction.fadeOut(crossFade);
      this.currentAction = null;
    }
    this.isPlaying = false;
  }

  update(dt) {
    if (this.mixer) {
      this.mixer.update(dt);
    }
  }
}
