"""Glissando, comme sur un piano : glisser d'une touche à l'autre les joue tour à tour."""
from conftest import power_on

ESPION = """() => { const e = window.__fw, log = window.__glog = [];
  const down = e.keyDown.bind(e), up = e.keyUp.bind(e);
  e.keyDown = (i, src) => { log.push(i); return down(i, src); };
  e.keyUp = (src) => { log.push('up'); return up(src); }; }"""


def rangee_basse(page):
    """Les centres des touches de la rangée du bas, de gauche à droite : [index, x, y]."""
    return page.evaluate("""() => {
      const hits = [...document.querySelectorAll('.keybed .hit')];
      hits[0].scrollIntoView({ block: 'center' });
      const r = hits.map((h, i) => { const b = h.getBoundingClientRect(); return [i, b.left + b.width / 2, b.top + b.height / 2, b.top]; });
      const bas = Math.max(...r.map((x) => x[3]));
      return r.filter((x) => x[3] > bas - 5).sort((a, b) => a[1] - b[1]).map((x) => x.slice(0, 3)); }""")


def test_glisser_joue_chaque_touche(page):
    power_on(page)
    page.evaluate(ESPION)
    (a, xa, y), (b, _, _), (c, xc, _) = rangee_basse(page)[:3]
    page.mouse.move(xa, y)
    page.mouse.down()
    page.mouse.move(xc, y, steps=1)                  # un seul saut : la touche du milieu sonne quand même
    assert page.evaluate("window.__glog") == [a, "up", b, "up", c]
    tenues = page.evaluate("[...document.querySelectorAll('.key.held')].map((k) => { const r = k.getBoundingClientRect(); return [r.left, r.right]; })")
    assert len(tenues) == 1 and tenues[0][0] < xc < tenues[0][1]     # seule la touche sous le doigt est enfoncée
    page.mouse.up()
    assert page.evaluate("window.__glog") == [a, "up", b, "up", c, "up"]
    assert page.evaluate("window.__fw.keyNotes.size") == 0


def test_hors_des_touches_la_derniere_reste_tenue(page):
    power_on(page)
    page.evaluate(ESPION)
    (a, xa, y), *_ = rangee_basse(page)
    page.mouse.move(xa, y)
    page.mouse.down()
    bas = page.viewport_size["height"] - 2
    assert not page.evaluate("([x, y]) => !!document.elementFromPoint(x, y)?.closest('.keybed')", [xa, bas])
    page.mouse.move(xa, bas, steps=4)                # vers le bas, hors du clavier
    assert page.evaluate("window.__glog") == [a]
    page.mouse.up()
    assert page.evaluate("window.__glog") == [a, "up"]


def test_glisser_au_doigt(page):
    """Au toucher (iPad), deux doigts glissent chacun de leur côté."""
    power_on(page)
    page.evaluate(ESPION)
    bas = rangee_basse(page)
    (a, xa, y), (b, _, _), (c, xc, _) = bas[:3]
    (d, xd, _), (e, xe, _) = bas[-2:]
    cdp = page.context.new_cdp_session(page)
    cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
    doigts = lambda *pts: [{"x": x, "y": y, "id": n} for n, x in pts]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": doigts((1, xa), (2, xe))})
    for t in (0.5, 1):                               # le premier vers la droite, le second vers la gauche
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": doigts((1, xa + (xc - xa) * t), (2, xe + (xd - xe) * t))})
    log = page.evaluate("window.__glog")
    assert [k for k in log if k in (a, b, c)] == [a, b, c] and [k for k in log if k in (d, e)] == [e, d], log
    assert log.count("up") == 3, log
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert page.evaluate("window.__glog").count("up") == 5 and page.evaluate("window.__fw.keyNotes.size") == 0
