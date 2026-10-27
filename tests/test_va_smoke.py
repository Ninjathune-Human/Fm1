"""Non-régression de la réimplémentation FM-1+VA."""
from conftest import lit_pixels, power_on


def test_power_on(page):
    power_on(page)
    page.evaluate("window.__fw.keyDown(12, 't')")
    page.wait_for_timeout(300)
    page.evaluate("window.__fw.keyUp('t')")
    assert lit_pixels(page) >= 1000
    assert page.evaluate("window.__fw.on") is True


def test_tuning(page):
    power_on(page)
    # A4 = MIDI 69 ; la touche 0 vaut KEY0 = 53 (F3) à l'octave 0, donc l'index 16
    idx = page.evaluate("69 - 53 - 12 * window.__fw.octave - window.__fw.kbdTr")
    page.evaluate("window.__fw.analyser.fftSize = 32768")
    page.evaluate(f"window.__fw.keyDown({idx}, 'a4')")
    page.wait_for_timeout(1200)
    peak = page.evaluate("""() => {
      const an = window.__fw.analyser, sr = an.context.sampleRate, d = new Float32Array(an.frequencyBinCount);
      an.getFloatFrequencyData(d);
      const hz = (i) => i * sr / an.fftSize;
      let best = -1;
      for (let i = 1; i < d.length - 1; i++) if (hz(i) > 400 && hz(i) < 480 && (best < 0 || d[i] > d[best])) best = i;
      const a = d[best - 1], b = d[best], c = d[best + 1];
      return hz(best + 0.5 * (a - c) / (a - 2 * b + c));
    }""")
    page.evaluate("window.__fw.keyUp('a4')")
    assert abs(peak - 440) <= 3, peak
