// La vérification de l'app dans le simulateur (action GitHub iPad) : un corps de fonction, exécuté par
// callAsyncJavaScript une fois la page chargée ; il rend en JSON ce que la page obtient de l'app.
const r = { securise: isSecureContext, page: typeof window.FM1LANG };
const etape = async (nom, f) => { try { r[nom] = await f(); } catch (e) { r[nom] = "échec : " + ((e && e.message) || e); } };
const octets = async (u) => { const x = await fetch(u); if (!x.ok) throw new Error(u + " " + x.status); return x.arrayBuffer(); };
await etape("coeur", async () => (await octets("runtime/fm1_web.wasm")).byteLength);
await etape("compile", async () => { await WebAssembly.compile(await octets("runtime/fm1_web.wasm")); return "ok"; });
await etape("natifs", async () => Object.keys(await (await fetch("natif/manifest.json")).json()).length);
await etape("module", async () => { await import("./runtime/persistence.js"); return "ok"; });
await etape("worklet", async () => { await new OfflineAudioContext(2, 128, 48000).audioWorklet.addModule("runtime/worklet.js"); return "ok"; });
await etape("absent", async () => (await fetch("absent.json")).status);
// un firmware « en ligne » (thefirmwarehub.com), pour information : il dépend du réseau et de son serveur
await etape("enLigne", async () => {
  const e = (await (await fetch("firmwares/catalogue.json")).json()).firmwares.find((e) => e.paquet_en_ligne && !e.fichier);
  return e.id + " " + (await octets(e.paquet_en_ligne)).byteLength;
});
return JSON.stringify(r);
