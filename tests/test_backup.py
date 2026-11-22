"""La sauvegarde et la restauration (reprises du fork jpawlik/Fm1) : localStorage du Solo et du Duo, et les bases
IndexedDB des firmwares natifs et émulés."""
import json

from conftest import power_on


def run(page, code):
    return page.evaluate(code)


def test_backup_round_trip_all_storage_families(page):
    page.goto(page.base + "index.html")
    output = run(page, """async () => {
      localStorage.setItem("fm1va.bank", '["my patch"]');
      localStorage.setItem("fm1b.fm1va.patterns", '["duo pattern"]');
      localStorage.setItem("fm1.duo.link", "1");
      localStorage.setItem("unrelated", "leave alone");
      const mod = await import("./backup.js");
      // Initialize both IndexedDB schemas before populating synthetic firmware saves.
      await mod.createBackup();
      const native = await new Promise((ok, ko) => {
        const r = indexedDB.open("fm1-natif", 1);
        r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error);
      });
      await new Promise((ok, ko) => {
        const tx = native.transaction("flash", "readwrite");
        tx.objectStore("flash").put({ 0: new Uint8Array([4, 5, 6]), 4096: new Uint8Array(4096) }, "hortator");
        tx.oncomplete = ok; tx.onerror = () => ko(tx.error);
      });
      native.close();
      const emu = await new Promise((ok, ko) => {
        const r = indexedDB.open("fm1-emulator", 2);
        r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error);
      });
      const hash = "a".repeat(64);
      await new Promise((ok, ko) => {
        const tx = emu.transaction(["packages","states","entries"],"readwrite");
        tx.objectStore("packages").put(new Uint8Array([0, 1, 2, 3]), hash);
        tx.objectStore("states").put({version:1, revision:4,
          sectors:[{at:0, data:new Uint8Array([1, 2, 3])}]}, hash);
        tx.objectStore("entries").put({hash}, "fm1.hortator");
        tx.oncomplete = ok; tx.onerror = () => ko(tx.error);
      });
      emu.close();
      // B's CPU emulator must be isolated even when the same firmware hash loads.
      const emuB = await new Promise((ok, ko) => {
        const r = indexedDB.open("fm1-emulator-b", 2);
        r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error);
      });
      await new Promise((ok, ko) => {
        const tx = emuB.transaction(["packages","states","entries"],"readwrite");
        tx.objectStore("packages").put(new Uint8Array([0, 1, 2, 3]), hash);
        tx.objectStore("states").put({version:1, revision:12,
          sectors:[{at:0, data:new Uint8Array([9, 8, 7])}]}, hash);
        tx.objectStore("entries").put({hash}, "fm1.hortator");
        tx.oncomplete = ok; tx.onerror = () => ko(tx.error);
      });
      emuB.close();
      const backup = await mod.createBackup();
      const data = JSON.parse(JSON.stringify(backup));
      localStorage.setItem("fm1va.bank", '["changed"]');
      localStorage.setItem("fm1va.random", "will be deleted");
      await mod.restoreBackup(data);
      const final = await mod.createBackup();
      const afterNative = final.databases["fm1-natif"].flash.find(([key]) => key[1] === "hortator");
      const afterEmu = final.databases["fm1-emulator"];
      const snap = {
        backup: backup.format, version: backup.version,
        local: localStorage.getItem("fm1va.bank"),
        duo: localStorage.getItem("fm1b.fm1va.patterns"),
        link: localStorage.getItem("fm1.duo.link"),
        removed: localStorage.getItem("fm1va.random"),
        unrelated: localStorage.getItem("unrelated"),
        nativeUnchanged: JSON.stringify(afterNative) === JSON.stringify(backup.databases["fm1-natif"].flash.find(([key]) => key[1] === "hortator")),
        emuUnchanged: JSON.stringify(afterEmu) === JSON.stringify(backup.databases["fm1-emulator"]),
        duoEmuUnchanged: JSON.stringify(final.databases["fm1-emulator-b"]) === JSON.stringify(backup.databases["fm1-emulator-b"]),
        separateSaves: JSON.stringify(afterEmu.states) !== JSON.stringify(final.databases["fm1-emulator-b"].states),
      };
      return snap;
    }""")
    assert output == {
        "backup": "fm1-fork-backup", "version": 1,
        "local": '["my patch"]', "duo": '["duo pattern"]', "link": "1",
        "removed": None, "unrelated": "leave alone",
        "nativeUnchanged": True, "emuUnchanged": True,
        "duoEmuUnchanged": True, "separateSaves": True,
    }


def test_invalid_backup_rejected_before_any_data_is_replaced(page):
    page.goto(page.base + "index.html")
    result = run(page, """async () => {
      const mod = await import("./backup.js");
      localStorage.setItem("fm1va.bank", "safe");
      const backup = await mod.createBackup();
      backup.databases["fm1-emulator"].packages = [[["string","bad-key"],["binary","Uint8Array","AA=="]]];
      let rejected = false;
      try { await mod.restoreBackup(backup); } catch (e) { rejected = e.message.includes("hash"); }
      return { rejected, preserved: localStorage.getItem("fm1va.bank") === "safe" };
    }""")
    assert result == {"rejected": True, "preserved": True}


def ouvre(page):
    page.click("#cp-btn")
    page.wait_for_selector("#cp-pop", state="visible")


def test_backup_export_button_downloads_json(page):
    page.goto(page.base + "index.html")
    assert page.locator("#aide-sauvegarde").count() == 1
    assert page.locator("#aide-sauvegarde button, #aide-sauvegarde input").count() == 0   # le volet explique, Mémoire agit
    ouvre(page)
    page.evaluate('localStorage.setItem("fm1va.global", "{\\"tempo\\":123}")')
    with page.expect_download() as event:
        page.locator("#backup-export").click()
    download = event.value
    assert download.suggested_filename.startswith("fm1-sauvegarde-")
    assert download.suggested_filename.endswith(".json")
    with open(download.path(), encoding="utf-8") as file:
        data = json.load(file)
    assert data["format"] == "fm1-fork-backup"
    assert ["fm1va.global", '{"tempo":123}'] in data["local"]
    assert set(data["databases"]) == {"fm1-natif", "fm1-emulator", "fm1-emulator-b"}
    assert data["copies"] == []                   # à part des bases : le fork ignore ce champ


def copie(page, nom, slot=""):
    """Une copie rangée comme le bouton Mémoire la range (clé : cadre du Duo, firmware, nom)."""
    page.evaluate("""async ([nom, slot]) => {
      const db = await new Promise((ok, ko) => { const r = indexedDB.open("fm1-copies", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("copies"); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      await new Promise((ok, ko) => { const t = db.transaction("copies", "readwrite");
        t.objectStore("copies").put({ id: "sloop", slot, nom, date: 1, kind: "emu", sectors: [{ at: 0, data: new Uint8Array([7, 8]) }] },
          slot + "\\u0000sloop\\u0000" + nom);
        t.oncomplete = ok; t.onerror = () => ko(t.error); });
      db.close();
    }""", [nom, slot])


def copies(page):
    return page.evaluate("""async () => {
      const db = await new Promise((ok, ko) => { const r = indexedDB.open("fm1-copies", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("copies"); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      const rows = await new Promise((ok, ko) => { const r = db.transaction("copies").objectStore("copies").getAll(); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      db.close();
      return rows.map((c) => [c.slot, c.nom, [...c.sectors[0].data]]).sort();
    }""")


def test_copies_dans_la_sauvegarde(page):
    """La sauvegarde reprend les copies (des deux FM-1 du Duo) ; la restaurer les remet telles quelles."""
    page.goto(page.base + "index.html")
    copie(page, "Avant")
    copie(page, "De B", "b")
    backup = page.evaluate("async () => JSON.parse(JSON.stringify(await (await import('./backup.js')).createBackup()))")
    assert len(backup["copies"]) == 2
    copie(page, "Après")
    page.evaluate("async (b) => (await import('./backup.js')).restoreBackup(b)", backup)
    assert copies(page) == [["", "Avant", [7, 8]], ["b", "De B", [7, 8]]]


def test_sauvegarde_sans_copies_les_garde(page):
    """Une sauvegarde d'avant, ou du fork, n'a pas de copies : la restaurer ne les touche pas."""
    page.goto(page.base + "index.html")
    copie(page, "Gardée")
    backup = page.evaluate("async () => { const b = JSON.parse(JSON.stringify(await (await import('./backup.js')).createBackup())); delete b.copies; return b; }")
    page.evaluate("async (b) => (await import('./backup.js')).restoreBackup(b)", backup)
    assert copies(page) == [["", "Gardée", [7, 8]]]


def test_restauration_bloquee_si_l_autre_fm1_du_duo_est_allume(page):
    page.goto(page.base + "index.html?duo")
    page.wait_for_function("window.__duo && window.__duo.frames.a.contentWindow.__fw && window.__duo.frames.b.contentWindow.__fw")
    page.frame(name="b").evaluate("document.getElementById('power').setAttribute('aria-checked', 'true')")
    result = page.frame(name="a").evaluate("""async () => {
      const mod = await import("./backup.js");
      try { await mod.restoreBackup(await mod.createBackup()); return "restaurée"; } catch (e) { return e.message; }
    }""")
    assert result == "Éteignez les deux FM-1 avant de restaurer"


def test_restore_blocked_when_synth_running(page):
    power_on(page)
    result = run(page, """async () => {
      const mod = await import("./backup.js");
      const b = await mod.createBackup();
      try { await mod.restoreBackup(b); return "incorrectly restored"; }
      catch (e) { return e.message; }
    }""")
    assert "Éteignez le FM-1" in result


def test_legacy_backup_restores_without_erasing_existing_duo_emulator(page):
    """Old version-1 backups lack the B database; preserve it instead of clearing it."""
    page.goto(page.base + "index.html")
    result = run(page, """async () => {
      const mod = await import("./backup.js");
      await mod.createBackup();
      const b = await new Promise((ok, ko) => {
        const r = indexedDB.open("fm1-emulator-b", 2);
        r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error);
      });
      await new Promise((ok, ko) => {
        const tx = b.transaction("entries", "readwrite");
        tx.objectStore("entries").put({hash: "f".repeat(64)}, "fm1.preserve");
        tx.oncomplete = ok; tx.onerror = () => ko(tx.error);
      });
      b.close();
      const backup = await mod.createBackup();
      delete backup.databases["fm1-emulator-b"]; // exported by previous main version
      await mod.restoreBackup(backup);
      const after = await mod.createBackup();
      return {
        oldVersionAccepted: backup.version === 1,
        retained: after.databases["fm1-emulator-b"].entries.some(([key]) => key[1] === "fm1.preserve")
      };
    }""")
    assert result == {"oldVersionAccepted": True, "retained": True}


def test_restored_duo_emulator_flash_is_independent(page):
    """Restoring a modern backup can replace B's states without altering A's."""
    page.goto(page.base + "index.html")
    result = run(page, """async () => {
      const mod = await import("./backup.js");
      await mod.createBackup();
      const insert = async (name, number) => {
        const db = await new Promise((ok, ko) => {
          const r = indexedDB.open(name, 2);
          r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error);
        });
        await new Promise((ok, ko) => {
          const tx = db.transaction("entries", "readwrite");
          tx.objectStore("entries").put({hash: "a".repeat(64), revision: number}, "fm1.amb");
          tx.oncomplete = ok; tx.onerror = () => ko(tx.error);
        });
        db.close();
      };
      await insert("fm1-emulator", 1);
      await insert("fm1-emulator-b", 2);
      const backup = await mod.createBackup();
      await insert("fm1-emulator", 3);
      await insert("fm1-emulator-b", 4);
      await mod.restoreBackup(backup);
      const after = await mod.createBackup();
      const from = (name) => after.databases[name].entries.find(([key]) => key[1] === "fm1.amb")[1][1];
      return [from("fm1-emulator").find(([key]) => key === "revision")[1][1],
              from("fm1-emulator-b").find(([key]) => key === "revision")[1][1]];
    }""")
    assert result == [1, 2]


def test_volet_en_anglais(page):
    page.goto(page.base + "index.html")
    page.click(".mast .lang [data-l=en]")
    page.wait_for_function("document.querySelector('#aide-sauvegarde summary').textContent === 'Backup and restore'")
    assert "in the Memory button" in page.text_content("#aide-sauvegarde")
    assert page.inner_text("#cp-btn") == "Memory"
    ouvre(page)
    assert page.text_content("#backup-export") == "Export a backup…"
    assert page.text_content("#cp-exp") == "Export the copy…"
    assert "Import…" in page.text_content("label[for=cp-imp]")
    assert page.text_content("#cp-msg").startswith("A backup keeps the whole FM-1")
    # un compte rendu écrit en français par backup.js passe en anglais
    page.evaluate("document.getElementById('cp-msg').textContent = 'Fichier trop lourd.'")
    page.wait_for_function("document.getElementById('cp-msg').textContent === 'File too large.'")


def test_restauration_par_importer(page):
    page.goto(page.base + "index.html")
    ouvre(page)
    page.evaluate('localStorage.setItem("fm1va.global", "avant")')
    with page.expect_download() as event:
        page.locator("#backup-export").click()
    path = event.value.path()
    page.evaluate('localStorage.setItem("fm1va.global", "après")')
    page.once("dialog", lambda d: d.accept())
    with page.expect_navigation():
        page.set_input_files("#cp-imp", path)
    assert page.evaluate('localStorage.getItem("fm1va.global")') == "avant"


def sample(page, sid):
    """Un sample du module sample, rangé comme le module le range (clé : son id)."""
    page.evaluate("""async (sid) => {
      const db = await new Promise((ok, ko) => { const r = indexedDB.open("fm1-samples", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("samples"); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      await new Promise((ok, ko) => { const t = db.transaction("samples", "readwrite");
        t.objectStore("samples").put({ id: sid, name: "T", rate: 44100, ch: [Float32Array.of(0.25, -0.5)], bars: null, fit: 1,
          slices: new Int32Array(17), pads: new Array(16).fill(null), cols: [] }, sid);
        t.oncomplete = ok; t.onerror = () => ko(t.error); });
      db.close();
    }""", sid)


def samples(page):
    return page.evaluate("""async () => {
      const db = await new Promise((ok, ko) => { const r = indexedDB.open("fm1-samples", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("samples"); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      const rows = await new Promise((ok, ko) => { const r = db.transaction("samples").objectStore("samples").getAll(); r.onsuccess = () => ok(r.result); r.onerror = () => ko(r.error); });
      db.close();
      return rows.map((s) => [s.id, s.ch[0] instanceof Float32Array, [...s.ch[0]]]).sort();
    }""")


def test_samples_dans_la_sauvegarde(page):
    """La sauvegarde reprend les samples du module ; la restaurer les remet tels quels (Float32Array compris)."""
    page.goto(page.base + "index.html")
    sample(page, "S01"); sample(page, "S02")
    backup = page.evaluate("async () => JSON.parse(JSON.stringify(await (await import('./backup.js')).createBackup()))")
    assert len(backup["samples"]) == 2
    sample(page, "S03")
    page.evaluate("async (b) => (await import('./backup.js')).restoreBackup(b)", backup)
    assert samples(page) == [["S01", True, [0.25, -0.5]], ["S02", True, [0.25, -0.5]]]


def test_sauvegarde_sans_samples_les_garde(page):
    """Une sauvegarde d'avant, ou du fork, n'a pas de samples : la restaurer ne les touche pas."""
    page.goto(page.base + "index.html")
    sample(page, "S01")
    backup = page.evaluate("async () => { const b = JSON.parse(JSON.stringify(await (await import('./backup.js')).createBackup())); delete b.samples; return b; }")
    page.evaluate("async (b) => (await import('./backup.js')).restoreBackup(b)", backup)
    assert samples(page) == [["S01", True, [0.25, -0.5]]]
