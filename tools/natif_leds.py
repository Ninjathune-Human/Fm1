#!/usr/bin/env python3
"""Les LED d'un firmware natif, pour que le panneau dessine chaque niveau comme l'appareil l'allume (index.html, ledConsts,
NativeFirmware.setDuty). Lancé par natif_build.sh :
  natif_leds.py consts <dépôt>   les constantes relevées dans ses sources, en un objet JSON sur une ligne ({} si rien) :
                                 la lueur et le niveau moyen de felucca-bsp (FM1_LED_DIM_NS, _DIM_LO_NS, _MID_N, _MID_N_LO),
                                 le haut d'une respiration (FM1_LED_BREATH_PK, _PK_LO), la lueur d'un HAL GATOR (FM1_GLOW_NS),
                                 les niveaux de ChoralRoot (FM1_LED_DIM2_NS, FM1_LED_FAINT_NS), les touches tamisées de FiMba
                                 (FM1_LED_DIM), la lueur des boutons de la famille X0X (GLOW_DIV, glow_on à l'allumage)
  natif_leds.py patch <dépôt>    avant la compilation : ce que l'appareil allume et que sa version navigateur garde pour
                                 elle, exporté (la lueur des boutons X0X, plat_glow ; la force de la lueur de fm1-base et son
                                 niveau moyen ; le rétroéclairage de Ravel, plat_backlight)
  natif_leds.py worklet <worklet.js>   après : son image les donne au panneau (glow, gl, mid)"""
import json, os, re, sys

NAMES = {"FM1_LED_DIM_NS": "dim_ns", "FM1_LED_DIM_LO_NS": "dim_lo_ns", "FM1_LED_MID_N": "mid_n", "FM1_LED_MID_N_LO": "mid_n_lo",
         "FM1_LED_BREATH_PK": "br_pk", "FM1_LED_BREATH_PK_LO": "br_pk_lo", "FM1_GLOW_NS": "glow_ns",
         "FM1_LED_DIM2_NS": "dim2_ns", "FM1_LED_FAINT_NS": "faint_ns", "FM1_LED_DIM": "dim_div", "GLOW_DIV": "glow_div"}
DEFINE = re.compile(r"^\s*#\s*define\s+(" + "|".join(NAMES) + r")\s+(\d+)u?\b", re.M)
GLOW_ON = re.compile(r"^static\s+uint8_t\s+glow_on\s*=\s*([01])\b", re.M)
SKIP = {"third_party", "node_modules", "vendor", "tests", "test", ".git", "build"}
EXPORT = '__attribute__((used, visibility("default")))'


def sources(root):
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        yield from (os.path.join(d, n) for n in names if n.endswith((".h", ".c")))


def read(f):
    try:
        return open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def rank(path):                       # le HAL de l'appareil d'abord, puis le reste du firmware, la version web en dernier
    p = path.replace(os.sep, "/")
    return (0 if "/hal/" in p or "/bsp/" in p else 1 if "/firmware/" in p or "/src/" in p else 2, p.count("/"), p)


def consts(root):
    out = {}
    for f in sorted(sources(root), key=rank):
        text = read(f)
        for name, value in DEFINE.findall(text):
            out.setdefault(NAMES[name], int(value))
        if os.path.basename(f) == "plat_fm1.c" and "glow_def" not in out:
            m = GLOW_ON.search(text)
            if m:
                out["glow_def"] = int(m.group(1))
    return out


def patch(root):
    done = []
    for f in sources(root):
        p = f.replace(os.sep, "/")
        if "/host/" not in p:                 # (les versions navigateur compilent les fichiers host/ de leur simulateur)
            continue
        text = read(f); new = text
        # la famille X0X : la lueur des boutons éteints (plat_glow), sur l'appareil une image sur GLOW_DIV
        if re.search(r"^void plat_glow\(int on\)", new, re.M) and "web_glow(" not in new:
            if re.search(r"^static int glow_on\b", new, re.M):
                new += f"\n{EXPORT} int web_glow(void) {{ return glow_on != 0; }}   /* (FM-1 : la lueur des boutons, pour le panneau) */\n"
            else:                             # (une version qui l'ignore : son état gardé quand même)
                new = re.sub(r"^void plat_glow\(int on\)", "static void plat_glow_0(int on);\nstatic int web_glow_v = -1;\n"
                             "void plat_glow(int on) { web_glow_v = on != 0; plat_glow_0(on); }\nstatic void plat_glow_0(int on)",
                             new, count=1, flags=re.M)
                new += f"\n{EXPORT} int web_glow(void) {{ return web_glow_v; }}   /* (FM-1 : la lueur des boutons, pour le panneau) */\n"
        # fm1-base : la force de la lueur (plat_lights : 1 DIM LO, 2 DIM HI) et les touches au niveau moyen (plat_lights_mid)
        if re.search(r"^static int lights_glow;", new, re.M) and "web_glow_level(" not in new:
            new += f"\n{EXPORT} int web_glow_level(void) {{ return lights_glow; }}   /* (FM-1 : la force de la lueur) */\n"
            if re.search(r"^static uint32_t mid_keys;", new, re.M):
                new += f"{EXPORT} uint32_t web_mid_keys(void) {{ return mid_keys; }}   /* (FM-1 : le niveau moyen) */\n"
        # Ravel : le rétroéclairage des LED éteintes (plat_backlight : 0 rien, 1 une image sur 6, 2 sur 3, 3 sur 2)
        stub = re.compile(r"^void plat_backlight\(int level\) \{ \(void\)level; \}", re.M)
        if stub.search(new) and "web_backlight(" not in new:
            new = stub.sub("static int web_back_v = -1;\nvoid plat_backlight(int level) { web_back_v = level & 3; }", new, count=1)
            new += f"\n{EXPORT} int web_backlight(void) {{ return web_back_v; }}   /* (FM-1 : le rétroéclairage) */\n"
        if new != text:
            open(f, "w", encoding="utf-8").write(new)
            done.append(p)
    return done


FRAME = 'type: "frame", buttons: ex.web_lit_buttons() >>> 0'


def worklet(f):
    text = read(f)
    if FRAME not in text:
        return False
    text = text.replace(FRAME, 'type: "frame", glow: ex.web_glow ? ex.web_glow() | 0 : -1, gl: ex.web_glow_level ? ex.web_glow_level() | 0 : -1, '
                        'mid: ex.web_mid_keys ? ex.web_mid_keys() >>> 0 : 0, buttons: ex.web_lit_buttons() >>> 0')
    open(f, "w", encoding="utf-8").write(text)
    return True


if __name__ == "__main__":
    cmd, arg = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("consts", sys.argv[1] if len(sys.argv) > 1 else ".")
    if cmd == "consts":
        print(json.dumps(consts(arg), separators=(",", ":")))
    elif cmd == "patch":
        for p in patch(arg):
            print("LED exportées :", p)
    elif cmd == "worklet":
        print("worklet : lueur, force et niveau moyen dans l'image" if worklet(arg) else "worklet : inchangé")
    else:
        sys.exit("natif_leds.py consts|patch|worklet <chemin>")
