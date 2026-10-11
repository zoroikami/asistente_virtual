/**
 * calibrator.js — Panel de calibración interactivo en vivo con lil-gui.
 * Permite ajustar en tiempo real los ángulos de brazos, codos, hombros,
 * cabeza y columna del modelo VRM, y copiar la pose resultante en formato JSON.
 */

import GUI from 'lil-gui';

export class YizeCalibrator {
  constructor(animator) {
    this.animator = animator;
    this.gui = null;
    this.visible = false;
    this.mirrorArms = true;

    // Valores iniciales de calibración
    this.pose = {
      // Brazo derecho
      uz: 1.2,
      ux: -0.05,
      ly: 0.2,
      lz: 0.0,
      shz: 0.0,
      curl: 0.3,

      // Brazo izquierdo (si no está espejado)
      l_uz: 1.2,
      l_ux: -0.05,
      l_ly: 0.2,
      l_lz: 0.0,
      l_shz: 0.0,
      l_curl: 0.3,

      // Cabeza y columna
      headX: 0.0,
      headY: 0.0,
      headZ: 0.0,
      spineX: 0.0,
      spineZ: 0.0,
    };

    this._initGUI();
  }

  _initGUI() {
    this.gui = new GUI({ title: '💜 Yize Pose Calibrator (F2)' });
    this.gui.domElement.style.position = 'fixed';
    this.gui.domElement.style.top = '10px';
    this.gui.domElement.style.left = '10px';
    this.gui.domElement.style.zIndex = '999999';
    this.gui.domElement.style.opacity = '0.92';
    this.gui.domElement.style.maxHeight = '90vh';
    this.gui.domElement.style.overflowY = 'auto';

    // Iniciar oculto
    this.gui.hide();
    this.visible = false;

    // Opciones generales
    const fGeneral = this.gui.addFolder('Control General');
    fGeneral.add(this, 'mirrorArms').name('Espejar Ambos Brazos').onChange(() => this.apply());

    // Brazo Derecho
    const fRight = this.gui.addFolder('Brazo Derecho');
    fRight.add(this.pose, 'uz', -1.5, 2.5, 0.02).name('uz (Bajar/Subir)').onChange(() => this.apply());
    fRight.add(this.pose, 'ux', -1.5, 1.5, 0.02).name('ux (Swing Adelante)').onChange(() => this.apply());
    fRight.add(this.pose, 'ly', -0.5, 2.8, 0.02).name('ly (Codo Flexión)').onChange(() => this.apply());
    fRight.add(this.pose, 'lz', -2.0, 2.0, 0.02).name('lz (Antebrazo Frontal)').onChange(() => this.apply());
    fRight.add(this.pose, 'shz', -0.6, 0.6, 0.01).name('shz (Hombro)').onChange(() => this.apply());
    fRight.add(this.pose, 'curl', 0.0, 1.0, 0.05).name('curl (Dedos)').onChange(() => this.apply());

    // Brazo Izquierdo (independiente)
    const fLeft = this.gui.addFolder('Brazo Izquierdo (Individual)');
    fLeft.add(this.pose, 'l_uz', -1.5, 2.5, 0.02).name('uz').onChange(() => this.apply());
    fLeft.add(this.pose, 'l_ux', -1.5, 1.5, 0.02).name('ux').onChange(() => this.apply());
    fLeft.add(this.pose, 'l_ly', -0.5, 2.8, 0.02).name('ly').onChange(() => this.apply());
    fLeft.add(this.pose, 'l_lz', -2.0, 2.0, 0.02).name('lz').onChange(() => this.apply());
    fLeft.add(this.pose, 'l_shz', -0.6, 0.6, 0.01).name('shz').onChange(() => this.apply());
    fLeft.add(this.pose, 'l_curl', 0.0, 1.0, 0.05).name('curl').onChange(() => this.apply());
    fLeft.close();

    // Cabeza y Columna
    const fHead = this.gui.addFolder('Cabeza & Columna');
    fHead.add(this.pose, 'headX', -0.4, 0.4, 0.01).name('Head X (Arriba/Abajo)').onChange(() => this.apply());
    fHead.add(this.pose, 'headY', -0.4, 0.4, 0.01).name('Head Y (Giro)').onChange(() => this.apply());
    fHead.add(this.pose, 'headZ', -0.4, 0.4, 0.01).name('Head Z (Ladeo)').onChange(() => this.apply());
    fHead.add(this.pose, 'spineX', -0.2, 0.2, 0.01).name('Spine X').onChange(() => this.apply());
    fHead.add(this.pose, 'spineZ', -0.2, 0.2, 0.01).name('Spine Z').onChange(() => this.apply());

    // Acciones y Botones
    const actions = {
      copiarJSON: () => this.copyToClipboard(),
      restablecer: () => this.reset(),
      baila: () => this.animator?.toggleDancing(),
    };

    const fActions = this.gui.addFolder('Herramientas');
    fActions.add(actions, 'copiarJSON').name('📋 Copiar Pose JSON');
    fActions.add(actions, 'restablecer').name('🔄 Restablecer Pose');
    fActions.add(actions, 'baila').name('💃 Probar Baile');
  }

  apply() {
    if (!this.animator) return;

    const r = {
      uz: this.pose.uz,
      ux: this.pose.ux,
      ly: this.pose.ly,
      lz: this.pose.lz,
      shz: this.pose.shz,
      curl: this.pose.curl,
    };

    const l = this.mirrorArms
      ? { ...r }
      : {
          uz: this.pose.l_uz,
          ux: this.pose.l_ux,
          ly: this.pose.l_ly,
          lz: this.pose.l_lz,
          shz: this.pose.l_shz,
          curl: this.pose.l_curl,
        };

    const override = {
      r,
      l,
      head: { x: this.pose.headX, y: this.pose.headY, z: this.pose.headZ },
      spine: { x: this.pose.spineX, z: this.pose.spineZ },
    };

    this.animator.setPoseOverride(override);
  }

  reset() {
    if (this.animator) {
      this.animator.setPoseOverride(null);
    }
    this.pose.uz = 1.2;
    this.pose.ux = -0.05;
    this.pose.ly = 0.2;
    this.pose.lz = 0.0;
    this.pose.shz = 0.0;
    this.pose.curl = 0.3;
    this.pose.headX = 0;
    this.pose.headY = 0;
    this.pose.headZ = 0;
    this.pose.spineX = 0;
    this.pose.spineZ = 0;
    this.gui.controllersRecursive().forEach((c) => c.updateDisplay());
  }

  copyToClipboard() {
    const jsonOutput = {
      both: this.mirrorArms
        ? {
            uz: Number(this.pose.uz.toFixed(2)),
            ux: Number(this.pose.ux.toFixed(2)),
            ly: Number(this.pose.ly.toFixed(2)),
            lz: Number(this.pose.lz.toFixed(2)),
            shz: Number(this.pose.shz.toFixed(2)),
            curl: Number(this.pose.curl.toFixed(2)),
          }
        : undefined,
      r: !this.mirrorArms
        ? {
            uz: Number(this.pose.uz.toFixed(2)),
            ux: Number(this.pose.ux.toFixed(2)),
            ly: Number(this.pose.ly.toFixed(2)),
            lz: Number(this.pose.lz.toFixed(2)),
            shz: Number(this.pose.shz.toFixed(2)),
            curl: Number(this.pose.curl.toFixed(2)),
          }
        : undefined,
      l: !this.mirrorArms
        ? {
            uz: Number(this.pose.l_uz.toFixed(2)),
            ux: Number(this.pose.l_ux.toFixed(2)),
            ly: Number(this.pose.l_ly.toFixed(2)),
            lz: Number(this.pose.l_lz.toFixed(2)),
            shz: Number(this.pose.l_shz.toFixed(2)),
            curl: Number(this.pose.l_curl.toFixed(2)),
          }
        : undefined,
      head: {
        x: Number(this.pose.headX.toFixed(2)),
        y: Number(this.pose.headY.toFixed(2)),
        z: Number(this.pose.headZ.toFixed(2)),
      },
      spine: {
        x: Number(this.pose.spineX.toFixed(2)),
        z: Number(this.pose.spineZ.toFixed(2)),
      },
    };

    const str = JSON.stringify(jsonOutput, null, 2);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(str).then(() => {
        console.log('✅ Pose copiada al portapapeles:\n', str);
        alert('✨ ¡Pose copiada al portapapeles en formato JSON!');
      });
    } else {
      console.log('📋 Pose JSON:\n', str);
    }
  }

  toggle() {
    this.visible = !this.visible;
    if (this.visible) {
      this.gui.show();
      this.apply();
    } else {
      this.gui.hide();
      this.animator?.setPoseOverride(null);
    }
    return this.visible;
  }
}
