// Web MIDI pour l'app iPad : WebKit n'a pas navigator.requestMIDIAccess, l'app le donne à la page avec le MIDI
// de l'iPad (CoreMIDI, FM1.swift). Les entrées seulement (un clavier) : chaque appareil branché en est une,
// outputs reste vide. L'app passe à la page principale les octets reçus (__fm1midi.rx) et la liste des
// appareils (__fm1midi.ports) ; elle les transmet à ses cadres (le Duo).
(() => {
  if (navigator.requestMIDIAccess || !window.webkit?.messageHandlers?.fm1midi) return;
  // la longueur d'un message d'après son statut
  const LEN = (s) => (s < 0xc0 || (s >= 0xe0 && s < 0xf0) || s === 0xf2 ? 3 : s < 0xe0 || s === 0xf1 || s === 0xf3 ? 2 : 1);
  const fire = (target, type, props) => {
    const e = Object.assign(new Event(type), props);
    target.dispatchEvent(e);
    if (target["on" + type]) target["on" + type](e);
  };

  class Input extends EventTarget {
    constructor(id, name) {
      super();
      Object.assign(this, { id, name, manufacturer: "", version: "", type: "input", state: "connected", connection: "open", onmidimessage: null, onstatechange: null });
      this.run = 0; this.msg = []; this.sysex = null;
    }
    // les octets de CoreMIDI, découpés en messages : statut courant (running status), SysEx sur plusieurs
    // paquets, temps réel (horloge) au milieu d'un message
    feed(bytes) {
      for (const b of bytes) {
        if (b >= 0xf8) { this.emit([b]); continue; }
        if (this.sysex) {
          if (b < 0x80) { this.sysex.push(b); continue; }
          if (b === 0xf7) { this.sysex.push(b); this.emit(this.sysex); this.sysex = null; continue; }
          this.sysex = null;                               // interrompu par un autre statut
        }
        if (b === 0xf0) { this.sysex = [b]; this.run = 0; this.msg = []; continue; }
        if (b >= 0x80) {
          this.run = b < 0xf0 ? b : 0; this.msg = [b];
          if (LEN(b) === 1) { if (b === 0xf6) this.emit(this.msg); this.msg = []; }
          continue;
        }
        if (!this.msg.length) { if (!this.run) continue; this.msg = [this.run]; }
        this.msg.push(b);
        if (this.msg.length === LEN(this.msg[0])) { this.emit(this.msg); this.msg = []; }
      }
    }
    emit(m) { fire(this, "midimessage", { data: Uint8Array.from(m) }); }
  }

  const inputs = new Map();
  let access = null, opened = null;
  // [[id, nom], ...] : les appareils branchés ; ceux qui partent restent, débranchés, comme dans Chrome
  const update = (list) => {
    const here = new Set(list.map(([id]) => id)), changed = [];
    for (const [id, name] of list) {
      const p = inputs.get(id);
      if (!p) { const n = new Input(id, name); inputs.set(id, n); changed.push(n); }
      else if (p.state !== "connected") { p.state = "connected"; p.connection = "open"; changed.push(p); }
    }
    for (const p of inputs.values()) if (p.state === "connected" && !here.has(p.id)) { p.state = "disconnected"; p.connection = "closed"; changed.push(p); }
    if (access) for (const port of changed) { fire(port, "statechange", { port }); fire(access, "statechange", { port }); }
  };
  const down = (f, ...args) => { for (let i = 0; i < window.frames.length; i++) try { window.frames[i].__fm1midi?.[f](...args); } catch { /* un cadre d'ailleurs */ } };

  navigator.requestMIDIAccess = () => (opened ??= window.webkit.messageHandlers.fm1midi.postMessage("ouvrir").then((list) => {
    update(list);
    access = Object.assign(new EventTarget(), { inputs, outputs: new Map(), sysexEnabled: true, onstatechange: null });
    return access;
  }));
  window.__fm1midi = {
    rx(id, bytes) { if (access) inputs.get(id)?.feed(bytes); down("rx", id, bytes); },
    ports(list) { update(list); down("ports", list); },
  };
})();
