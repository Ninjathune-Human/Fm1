// SPDX-License-Identifier: GPL-3.0-only
// Les firmwares bâtis sur Dinghy (Bytemania, Scintilla) dans un AudioWorklet : leur app, sur notre hôte
// (tools/worklets/dinghy_host.c), compilée par tools/worklets/asyncify.sh, menée par la coroutine de coroutine.js.
import { Coroutine } from "./coroutine.js";

class Dinghy extends Coroutine {
  constructor() { super(); this.LIT = 1; }
  restore(ex, s) {                                       // les réglages et la bibliothèque, gardés par la page
    if (s.store && s.store.length === ex.web_store_n()) new Uint8Array(ex.memory.buffer, ex.web_store(), s.store.length).set(s.store);
  }
  keep(ex) {
    return ex.web_store_take_dirty() ? { store: new Uint8Array(ex.memory.buffer, ex.web_store(), ex.web_store_n()).slice() } : null;
  }
  block(ex) { return new Float32Array(ex.memory.buffer, ex.web_audio(), 512); }
  button(ex, i, down) { ex.web_btn(i, down); }
  keys(ex, mask) { ex.web_keys(mask); }
  enc(ex, id, n) { ex.web_enc(id, n); }
  master(ex, v) { ex.web_master(Math.round((v / 1023) * 4096)); }
  midi(ex, d) { ex.web_midi(d[0] | 0, d[1] | 0, d[2] | 0); }
}
registerProcessor("dinghy", Dinghy);
