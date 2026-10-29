// chipbox (pbarilla/chipbox, GPL-3.0) dans un AudioWorklet, d'après sa page (site/play/index.html, tests/host.c) :
// compilé par tools/worklets/asyncify.sh, mené par la coroutine de coroutine.js.
import { Coroutine } from "./coroutine.js";

class Chipbox extends Coroutine {
  constructor() { super(); this.LIT = 2; this.gain = 0.88; this.gen = 0; }   // ses LED : 2 allumée, 1 tamisée
  restore(ex, s) {                                       // ses projets (la flash) et ses réglages, gardés par la page
    const put = (b, p, n) => { if (b && b.length === n) new Uint8Array(ex.memory.buffer, p, n).set(b); };
    put(s.flash, ex.web_flash(), ex.web_flash_len());
    put(s.store, ex.web_store(), ex.web_store_len());
    this.gen = ex.web_flash_gen();
    ex.web_start();                                      // sa boucle attend que la page ait tout remis
  }
  keep(ex) {
    const g = ex.web_flash_gen();
    if (g === this.gen) return null;
    this.gen = g;
    return { flash: new Uint8Array(ex.memory.buffer, ex.web_flash(), ex.web_flash_len()).slice(),
             store: new Uint8Array(ex.memory.buffer, ex.web_store(), ex.web_store_len()).slice() };
  }
  block(ex) {                                            // Q15 ; le volume est celui de la page
    const a = new Int32Array(ex.memory.buffer, ex.web_audio(), 512), f = new Float32Array(512), g = this.gain / 32768;
    for (let i = 0; i < 512; i++) { const v = a[i]; f[i] = (v > 32767 ? 32767 : v < -32767 ? -32767 : v) * g; }
    return f;
  }
  button(ex, i, down) { ex.web_button(i, down); }
  keys(ex, mask) { ex.web_keys(mask); }
  enc(ex, id, n) { ex.web_enc(id, n); }
  master(ex, v) { this.gain = v / 1023; }
}
registerProcessor("chipbox", Chipbox);
