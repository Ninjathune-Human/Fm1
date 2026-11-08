/* SPDX-License-Identifier: GPL-3.0-only
 * Un FM-1 dans le navigateur pour les firmwares bâtis sur Dinghy (zvenson/dinghy) : Bytemania, Scintilla. Leur
 * platform.c inclut tests/host.c sous DINGHY_HOST ; l'action pose ce fichier à sa place (avant la compilation), avec
 * les mêmes fonctions que leur hôte (d'après tests/host.c de Dinghy), mais menées par la page plutôt que par un
 * script : app_main tourne en coroutine (tools/worklets/asyncify.sh), platform_poll rend la main tant que le temps
 * de l'audio n'a pas rattrapé la milliseconde suivante ; l'audio est tiré par le worklet (web_audio), les réglages et
 * la bibliothèque sont gardés par la page (web_store).
 *   -DDH_LIBC=1   l'hôte inclut libc.c (Scintilla), ses mem* renommés
 *   -DDH_CV_ROWS  les lignes du canevas de gfx.c (72 par défaut, Scintilla 64) */
#include <stdint.h>
#include <string.h>
#include <emscripten.h>

#ifndef APP_NAME
#define APP_NAME "DINGHY"
#endif
#ifndef APP_VER
#define APP_VER "web"
#endif
#ifndef DH_CV_ROWS
#define DH_CV_ROWS 72u
#endif
#define FS 44100u
#define HALF_FRAMES 256u

static volatile uint32_t fm1_ms;
#define FM1_TICKS_PER_US 24u
static uint32_t fm1_ticks(void) { return fm1_ms * 1000u * FM1_TICKS_PER_US; }   /* (pas de mesure du processeur) */
static struct { uint32_t notes, buttons; } fm1_in;
static uint32_t host_edges, host_rel;
static uint32_t fm1_input_edges(uint32_t *released)
{
    uint32_t b = host_edges;
    *released = host_rel;
    host_edges = host_rel = 0;
    return b;
}
static uint32_t fm1_input_note_edges(void) { return 0; }
static int32_t host_enc[7];
static int32_t fm1_enc_take(uint32_t e) { int32_t n = e < 7u ? host_enc[e] : 0; if (e < 7u) host_enc[e] = 0; return n; }
static uint8_t host_leds[41];
static void fm1_led_key(uint32_t id, int on) { if (id < 41u) host_leds[id] = on ? 1u : 0u; }

static uint16_t fb[240 * 240];                  /* RGB565 dans l'ordre de la machine (gfx.c envoie la dalle inversée) */
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{
    for (uint32_t j = y; j < y + h && j < 240u; j++)
        for (uint32_t i = x; i < x + w && i < 240u; i++) fb[j * 240u + i] = c;
}
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{
    for (uint32_t j = 0; j < h; j++)
        for (uint32_t i = 0; i < w; i++)
            if (x + i < 240u && y + j < 240u) { uint16_t c = px[j * w + i]; fb[(y + j) * 240u + x + i] = (uint16_t)(c >> 8 | c << 8); }
}
#if DH_LIBC
#undef memset
#undef memcpy
#define memset libc_memset
#define memcpy libc_memcpy
#define memcmp libc_memcmp
#include "libc.c"
#undef memset
#undef memcpy
#undef memcmp
#endif
#define CV_MAX (240u * DH_CV_ROWS)
#include "gfx.c"

/* les réglages (un secteur) et la bibliothèque (quatre), comme platform.c, en mémoire : un seul bloc pour la page */
#define LIB_SECTORS 4u
#define LIB_MAX (0x1000u - 12u)
static struct {
    uint8_t store[256 + 4];
    uint32_t lib_n[LIB_SECTORS], lib_magic[LIB_SECTORS];
    uint8_t lib[LIB_SECTORS][LIB_MAX];
} keep;
static int keep_dirty;
static int settings_load(void *p, uint32_t n)
{
    if (keep.store[0] != 1 || n > 256u) return -1;
    memcpy(p, keep.store + 4, n);
    return 0;
}
static int settings_save(const void *p, uint32_t n)
{
    if (n > 256u) return -1;
    keep.store[0] = 1;
    memcpy(keep.store + 4, p, n);
    keep_dirty = 1;
    return 0;
}
static int lib_load(uint32_t k, uint32_t magic, void *p, uint32_t n)
{
    if (k >= LIB_SECTORS || keep.lib_n[k] != n || keep.lib_magic[k] != magic) return -1;
    memcpy(p, keep.lib[k], n);
    return 0;
}
static int lib_save(uint32_t k, uint32_t magic, const void *p, uint32_t n)
{
    if (k >= LIB_SECTORS || n > LIB_MAX) return -1;
    memcpy(keep.lib[k], p, n);
    keep.lib_n[k] = n;
    keep.lib_magic[k] = magic;
    keep_dirty = 1;
    return 0;
}

static uint8_t mq[64][3];
static uint32_t mq_w, mq_r;
static int midi_get(uint8_t *st, uint8_t *d1, uint8_t *d2)
{
    if (mq_r == mq_w) return 0;
    *st = mq[mq_r % 64u][0]; *d1 = mq[mq_r % 64u][1]; *d2 = mq[mq_r % 64u][2];
    mq_r++;
    return 1;
}
static void midi_send(uint32_t st, uint32_t d1, uint32_t d2) { (void)st; (void)d1; (void)d2; }

static void app_audio(int32_t *out, uint32_t n);
static void app_main(void);

static double host_t0;
static void platform_poll(void)                 /* un appel = une milliseconde, au pas du temps de l'audio */
{
    fm1_ms++;
    while ((double)fm1_ms > emscripten_get_now() - host_t0) emscripten_sleep(1);
}
int main(void)
{
    host_t0 = emscripten_get_now();
    app_main();
    return 0;
}

/* ---- la page */
static int32_t host_blk[2u * HALF_FRAMES];
static float host_out[2u * HALF_FRAMES];
static uint32_t host_gain = 4096u;
EMSCRIPTEN_KEEPALIVE uint16_t *web_fb(void) { return fb; }
EMSCRIPTEN_KEEPALIVE uint8_t *web_leds(void) { return host_leds; }
EMSCRIPTEN_KEEPALIVE float *web_audio(void)
{
    memset(host_blk, 0, sizeof host_blk);
    app_audio(host_blk, HALF_FRAMES);
    for (uint32_t i = 0; i < 2u * HALF_FRAMES; i++) host_out[i] = (float)host_blk[i] * (float)host_gain * (1.0f / (32768.0f * 4096.0f));
    return host_out;
}
EMSCRIPTEN_KEEPALIVE void web_btn(uint32_t i, uint32_t down)    /* i : l'identifiant Dinghy (BTN_OCT_DOWN .. BTN_REC) */
{
    uint32_t bit = 1u << i;
    if (i >= 14u) return;
    if (down) { if (!(fm1_in.buttons & bit)) host_edges |= bit; fm1_in.buttons |= bit; }
    else { if (fm1_in.buttons & bit) host_rel |= bit; fm1_in.buttons &= ~bit; }
}
EMSCRIPTEN_KEEPALIVE void web_keys(uint32_t mask) { fm1_in.notes = mask & 0x7FFFFFFu; }
EMSCRIPTEN_KEEPALIVE void web_enc(uint32_t id, int32_t n) { if (id < 7u) host_enc[id] += n; }
EMSCRIPTEN_KEEPALIVE void web_master(uint32_t q12) { host_gain = q12 > 4096u ? 4096u : q12; }
EMSCRIPTEN_KEEPALIVE void web_midi(uint32_t st, uint32_t d1, uint32_t d2)
{
    if (st < 0x80u || mq_w - mq_r >= 64u) return;
    mq[mq_w % 64u][0] = (uint8_t)st; mq[mq_w % 64u][1] = (uint8_t)(d1 & 127u); mq[mq_w % 64u][2] = (uint8_t)(d2 & 127u);
    mq_w++;
}
EMSCRIPTEN_KEEPALIVE uint8_t *web_store(void) { return (uint8_t *)&keep; }
EMSCRIPTEN_KEEPALIVE uint32_t web_store_n(void) { return sizeof keep; }
EMSCRIPTEN_KEEPALIVE uint32_t web_store_take_dirty(void) { int d = keep_dirty; keep_dirty = 0; return (uint32_t)d; }
