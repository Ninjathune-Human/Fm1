// frodhes (leonardoMirabal/frodhes, GPL-3.0) dans un AudioWorklet, d'après sa page (web/app.js, web/web_hal.c) :
// compilé par tools/worklets/asyncify.sh, mené par la coroutine de coroutine.js.
import { Coroutine } from "./coroutine.js";

class Frodhes extends Coroutine {
  constructor() { super(); this.LIT = 1; }              // ses LED : 1 allumée, 2 la lueur
  restore(ex, s) {                                       // les réglages et les presets, gardés par la page
    if (s.store && s.store.length === ex.web_store_n()) new Uint8Array(ex.memory.buffer, ex.web_store(), s.store.length).set(s.store);
  }
  keep(ex) {
    return ex.web_store_take_dirty() ? { store: new Uint8Array(ex.memory.buffer, ex.web_store(), ex.web_store_n()).slice() } : null;
  }
  block(ex) { return new Float32Array(ex.memory.buffer, ex.web_audio(1), 512); }   // MASTER déjà appliqué
  button(ex, i, down) { ex.web_btn(i, down); }
  keys(ex, mask) { ex.web_keys(mask); }
  enc(ex, id, n) { ex.web_enc(id, n); }
  master(ex, v) { ex.web_master(Math.round((v / 1023) * 4096)); }
}
registerProcessor("frodhes", Frodhes);
