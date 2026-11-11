"""Ouvre à la page l'USB MIDI de fm1-emu : un câble vers un ordinateur, comme `fm1-live --usb`.

fm1-emu émule déjà l'hôte USB (fm1-soc usb.rs : l'énumération, puis le MIDI USB dans les deux sens, SysEx compris),
mais sa version navigateur ne s'en sert pas : le MIDI de la page arrive par la prise MIDI IN (l'UART). Ce script,
lancé par l'action GitHub sur la copie de fm1-emu, expose cet hôte (fm1_usb_plug, fm1_usb_state, fm1_usb_send,
fm1_usb_take, fm1_usb_buf) et le relaie dans le worklet : { type: "usb-plug" } branche le câble, { type: "usb", bytes }
envoie un message complet au FM-1, et ce que le FM-1 envoie revient en { type: "usb", bytes } (chaque message : sa
longueur sur 2 octets, poids faible d'abord, puis ses octets). Le protocole d'éditeur d'un firmware (SLOOP) en a besoin.
Rien d'autre ne change : sans "usb-plug", aucun câble, comme avant.
    python3 tools/fm1emu_usb.py <dossier fm1-emu> <worklet.js publié>
"""
import sys

emu, worklet = sys.argv[1], sys.argv[2]


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path} : motif introuvable ou multiple : {old[:60]!r}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


USB = '''/// USB (Fm1, tools/fm1emu_usb.py): the cable to a computer, the page, as fm1-live's --usb. The emulated FM-1
/// enumerates (fm1_soc::usb), then USB MIDI goes both ways, SysEx included.
#[no_mangle]
pub extern "C" fn fm1_usb_plug() {
    if let Some(m) = machine() {
        if !m.soc.usb.cable {
            m.soc.usb_plug();
        }
    }
}

/// 0: no cable; 1: the cable in, the device not configured yet; 2: a USB device configured on the bus.
#[no_mangle]
pub extern "C" fn fm1_usb_state() -> u32 {
    machine().map_or(0, |m| if m.soc.usb.product().is_some() { 2 } else { m.soc.usb.cable as u32 })
}

/// One complete MIDI message (SysEx included) from the computer to the device, at `ptr` (from fm1_alloc, consumed).
#[no_mangle]
pub extern "C" fn fm1_usb_send(ptr: *mut u8, len: u32) {
    // SAFETY: ptr/len come from fm1_alloc and JS filled them.
    let msg = unsafe { Vec::from_raw_parts(ptr, len as usize, len as usize) };
    if let Some(m) = machine() {
        m.soc.usb.midi_send(&msg);
    }
}

static mut USB_IN: Vec<u8> = Vec::new();
/// What the device sent the computer since the last call: each complete message as its length (2 bytes, LSB
/// first) then its bytes. Returns the total length; fm1_usb_buf says where (valid until the next call).
#[no_mangle]
#[allow(static_mut_refs)]
pub extern "C" fn fm1_usb_take() -> u32 {
    unsafe {
        USB_IN.clear();
        if let Some(m) = machine() {
            for msg in m.soc.usb.midi_take() {
                USB_IN.extend_from_slice(&(msg.len() as u16).to_le_bytes());
                USB_IN.extend_from_slice(&msg);
            }
        }
        USB_IN.len() as u32
    }
}

#[no_mangle]
#[allow(static_mut_refs)]
pub extern "C" fn fm1_usb_buf() -> *const u8 {
    unsafe { USB_IN.as_ptr() }
}

/// One MIDI byte into the MIDI IN jack'''

patch(f"{emu}/crates/fm1-web/src/lib.rs", [
    ("/// One MIDI byte into the MIDI IN jack", USB),
])
patch(worklet, [
    ('        else if (m.type === "midi") for (const b of m.bytes) this.x.fm1_midi(b);\n',
     '        else if (m.type === "midi") for (const b of m.bytes) this.x.fm1_midi(b);\n'
     '        else if (m.type === "usb-plug") this.x.fm1_usb_plug?.();         // USB : le câble (fm1emu_usb.py)\n'
     '        else if (m.type === "usb" && this.x.fm1_usb_send) {             // un message complet vers le FM-1\n'
     '          const p = this.x.fm1_alloc(m.bytes.length);\n'
     '          new Uint8Array(this.x.memory.buffer, p, m.bytes.length).set(m.bytes);\n'
     '          this.x.fm1_usb_send(p, m.bytes.length);\n'
     '        }\n'),
    ("    if (out[1]) out[1].set(r);\n",
     "    if (out[1]) out[1].set(r);\n"
     "    const usbN = x.fm1_usb_take ? x.fm1_usb_take() : 0;   // ce que le FM-1 a envoyé par l'USB (fm1emu_usb.py)\n"
     "    if (usbN) this.port.postMessage({ type: \"usb\", seq: this.seq, bytes: new Uint8Array(x.memory.buffer, x.fm1_usb_buf(), usbN).slice() });\n"),
    ("        short: this.short, halted: x.fm1_halted(),",
     "        usb: x.fm1_usb_state ? x.fm1_usb_state() : 0, short: this.short, halted: x.fm1_halted(),"),
])
print("fm1-emu : USB MIDI ouvert à la page")
