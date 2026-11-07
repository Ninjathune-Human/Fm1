/* SPDX-License-Identifier: GPL-3.0-only
 * Cut-A-Dor (kidbee85-beep/cut-a-dor-release, GPL-3.0) pour le panneau : son moteur (firmware/src/dsp/cad.c) et son
 * interface (firmware/src/app/ui.c, gfx.c) sur le contrat de plateforme de l'appli (app/plat.h), comme son simulateur
 * d'écran (host/display.c) les assemble, et menés comme main_fm1.c : une image d'interface toutes les 16 ms
 * (ui_frame), le son par blocs de 256 (cad_render). Ses deux objets de mémoire (le projet, le panneau) sont gardés
 * par la page. */
#include <stdint.h>
#include <string.h>
#include "cad.h"
#include "app/app.h"

static uint16_t pixels[240 * 240];                /* RGB565 dans l'ordre de la machine */
static uint32_t now, buttons, keys, master_q12 = 4096, lit_b, lit_k;
static int enc[NE], glow, play_red;
static uint8_t cad_edit_busy;
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{
    for (unsigned j = y; j < y + h && j < 240; j++)
        for (unsigned i = x; i < x + w && i < 240; i++) pixels[j * 240 + i] = c;
}
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *p)
{
    for (unsigned j = 0; j < h && j + y < 240; j++)
        for (unsigned i = 0; i < w && i + x < 240; i++) { uint16_t c = p[j * w + i]; pixels[(j + y) * 240 + i + x] = (uint16_t)((c >> 8) | (c << 8)); }
}
#include "gfx.c"

static uint8_t store[OBJ_NOBJ][PLAT_STORE_MAX];
static uint32_t store_len[OBJ_NOBJ];
#define MQ 64u
static uint32_t mq[MQ], mq_r, mq_w;

uint32_t plat_ms(void) { return now; }
uint32_t plat_buttons(void) { return buttons; }
uint32_t plat_keys(void) { return keys; }
int32_t plat_enc(int i) { int v = enc[i]; enc[i] = 0; return v; }
uint32_t plat_master(void) { return master_q12; }
void plat_leds(uint32_t b, uint32_t k) { lit_b = b; lit_k = k; }
void plat_glow(int on) { glow = on != 0; }
void plat_lighting(int level, int g) { (void)level; glow = g != 0; }
void plat_play_red(int red) { play_red = red != 0; }
uint32_t plat_cpu_pct(void) { return 0; }
uint32_t plat_xruns(void) { return 0; }
int plat_midi_in(uint32_t *p, uint32_t *t)
{
    if (mq_r == mq_w) return 0;
    *p = mq[mq_r++ % MQ]; *t = now;
    return 1;
}
void plat_midi_out(uint32_t p) { (void)p; }
int plat_store_load(uint32_t obj, void *dst, uint32_t max)
{
    uint32_t n;
    if (obj >= OBJ_NOBJ || !store_len[obj]) return -1;
    n = store_len[obj] < max ? store_len[obj] : max;
    memcpy(dst, store[obj], n);
    return (int)n;
}
int plat_store_save(uint32_t obj, const void *src, uint32_t len)
{
    if (obj >= OBJ_NOBJ || len > PLAT_STORE_MAX) return -1;
    memcpy(store[obj], src, len); store_len[obj] = len;
    return 0;
}
/* project.c, sans son attente du fil audio : ici, le rendu qui suit la commande d'export la sert aussitôt
 * (comme web_export de son moteur web) */
static int32_t audio[2 * 256];
int project_save(void)
{
    if (cad_view.playing) return -3;
    cad_command(A_QUIET, 0, 0);
    if (cad_command(A_EXPORT, 0, 1)) return -2;
    cad_render(audio, 0, master_q12);
    return plat_store_save(OBJ_PROJ, &cad_transfer, sizeof cad_transfer);
}
#include "app/ui.c"

static float out[2 * 256];
static uint32_t lights[8];

uint8_t *sim_store(void) { return &store[0][0]; }
uint32_t *sim_store_len(void) { return store_len; }
uint32_t sim_store_size(void) { return sizeof store; }
void sim_init(void)
{
    int n;
    cad_init();
    cad_render(0, 0, 4096);
    n = plat_store_load(OBJ_PROJ, &cad_transfer, sizeof cad_transfer);   /* project_load, project_apply */
    if (n > 0 && !cad_upgrade_transfer((unsigned)n)) { cad_command(A_IMPORT, 0, 0); cad_render(0, 0, 0); }
    ui_init();
}
void sim_btn(uint32_t b, uint32_t down) { if (b < NB) buttons = down ? buttons | 1u << b : buttons & ~(1u << b); }
void sim_key(uint32_t k, uint32_t down) { if (k < NKEYS) keys = down ? keys | 1u << k : keys & ~(1u << k); }
void sim_enc(uint32_t role, int32_t n) { if (role < NE) enc[role] += n; }
void sim_master(uint32_t v) { uint32_t k = v > 1023u ? 1023u : v; master_q12 = (k * k) >> 8; }
void sim_midi(uint32_t st, uint32_t d1, uint32_t d2)
{
    uint32_t cin = st >= 0xF0u ? 0xFu : st >> 4;
    if (st < 0x80u || mq_w - mq_r >= MQ) return;
    mq[mq_w++ % MQ] = cin | st << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24;
}
void sim_frame(void) { now += 16; ui_frame(); }
float *sim_render(void)
{
    cad_render(audio, 256, master_q12);
    for (unsigned i = 0; i < 2 * 256; i++) out[i] = (float)audio[i] * (1.0f / 8388607.0f);
    return out;
}
uint32_t sim_block(void) { return 256; }
uint16_t *sim_fb(void) { return pixels; }
/* les LED dans le modèle Felucca de la page : [0] les boutons (PLAY : bit 14 le vert, bit 10 le rouge en
 * enregistrement), [1] les touches, [2] la lueur des boutons éteints */
uint32_t *sim_leds(void)
{
    uint32_t b = lit_b & 0x3FFFu & ~(1u << B_PLAY);
    if (lit_b & 1u << B_PLAY) b |= play_red ? 1u << 10 : 1u << 14;
    lights[0] = b; lights[1] = lit_k; lights[2] = glow ? ~lit_b & 0x3FFFu : 0;
    return lights;
}
