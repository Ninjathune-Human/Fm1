"""Sonde (jamais publiée) : compte les lectures du bus par adresse dans les régions compilées, pour savoir lesquelles coûtent.
    python3 tools/probe_bus.py <dossier fm1-emu>   -> le rapport du profil (FM1_PROFILE=1) gagne un 3e élément {adresse: lectures}"""
import sys
emu = sys.argv[1]
def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path} : {old[:50]!r}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)
patch(f"{emu}/crates/fm1-core/src/jit_wasm.rs", [
    ("extern \"C\" fn h_read<B: Bus>(ctx: *mut Ctx, addr: u32, idx: u32, w: u32) -> u32 {\n",
     "pub static mut BUSHIST: Option<std::collections::HashMap<u32, u32>> = None;\n"
     "extern \"C\" fn h_read<B: Bus>(ctx: *mut Ctx, addr: u32, idx: u32, w: u32) -> u32 {\n"
     "    #[allow(static_mut_refs)] unsafe { *BUSHIST.get_or_insert_with(Default::default).entry(addr).or_insert(0) += 1; }\n"),
])
patch(f"{emu}/crates/fm1-web/src/lib.rs", [
    ("""    let report = machine().map(|m| format!("[{},{}]", m.cpu.jit_profile_json(),
        m.cpu1.as_ref().map_or_else(|| "null".to_owned(), |c| c.jit_profile_json()))).unwrap_or_else(|| "[]".to_owned());""",
     """    let hist = { #[cfg(target_arch = "wasm32")] { let mut v: Vec<(u32, u32)> = fm1_core::jit_wasm::BUSHIST.as_ref().map_or_else(Vec::new, |h| h.iter().map(|(a, n)| (*a, *n)).collect());
        v.sort_by(|a, b| b.1.cmp(&a.1)); v.truncate(24); format!("{{{}}}", v.iter().map(|(a, n)| format!("\\"{a:08x}\\":{n}")).collect::<Vec<_>>().join(",")) } #[cfg(not(target_arch = "wasm32"))] { "{}".to_owned() } };
    let report = machine().map(|m| format!("[{},{},{}]", m.cpu.jit_profile_json(),
        m.cpu1.as_ref().map_or_else(|| "null".to_owned(), |c| c.jit_profile_json()), hist)).unwrap_or_else(|| "[]".to_owned());"""),
])
