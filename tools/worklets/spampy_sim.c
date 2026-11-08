/* SPDX-License-Identifier: GPL-3.0-only
 * SPAMPY (Spampy-Droid/SPAMPY-0.0-r949, GPL-3.0) pour le panneau, comme MYCELIUM (mycelium_sim.c) : son test
 * d'interface (tests/ui_pages_test.c, inchangé, UI_PAGES_HARNESS_ONLY) assemble l'interface de l'appareil sur un
 * écran, des boutons et une flash factices, le son de hostsim.c ; on le mène comme main.c : felucca_init, puis une
 * image toutes les 16 ms (ui_input, ui_leds, ui_draw), le son par blocs de CTL (mix_block).
 * Les projets, les presets et les sections du test sont factices : rien n'est gardé. */
/* la matrice de l'appareil (hal/fm1_input.h, lignes 1 à 4, celles que led_pos_init lit), dans la forme 5 x 16 que le
 * test déclare vide : les LED retrouvent leur place */
static const signed char MY_KEYMAP[5][16] = {
    {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1},
    { 5, 11,  4, 10,  3,  9,  2,  8, -1, -1, -1, -1, -1, -1, -1, -1},
    {34, 35, 36, 37, 38, 40, 39, 13,  7,  6, 12, -1, -1, -1, -1, -1},
    {23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, -1, -1, -1, -1, -1},
    { 0,  1, 15, 14, 17, 16, 19, 18, 20, 21, 22, -1, -1, -1, -1, -1},
};
#define FM1_KEYMAP MY_KEYMAP
#define UI_PAGES_HARNESS_ONLY 1
#include "ui_pages_test.c"

static float sim_out[2 * 4096];
static uint32_t sim_lights[8];

void sim_init(void)                               /* main.c : settings_init, panel_init, felucca_init */
{
    uint32_t i;
    settings_init();
    panel = PANEL_DEFAULT;
    for (i = 0; i < G_COUNT; i++) song.g[i] = GP[i].def;
    fm6_init();
    for (i = 0; i < NTRK; i++) {
        track_t *t = &trk[i];
        track_defaults(t);
        if (i < NPART) {
            set_engine_of(t, TRK_DEF[i][0]);
            apply_preset_to(t, TRK_DEF[i][1]);
            t->engine = t->eng_req;
        }
        track_defaults_steps(t);
    }
    TDRUM->p[P_E0] = DRUM_DEFAULT_KIT;
    song.sel = 0;
    song.master_q12 = 2048;
    song.g[G_SYNC] = (int16_t)lights_sync;
    song.g[G_MIDI] = (int16_t)lights_mout;
    song.g[G_ROUTE] = (int16_t)lights_min;
    song.g[G_CH1] = midi_set[0], song.g[G_CH2] = midi_set[1], song.g[G_CH3] = midi_set[2];
    song.g[G_DRCH] = midi_set[3], song.g[G_CHOTH] = midi_set[4], song.g[G_BEND] = midi_set[5];
    song.g[G_FXCH] = midi_set[6];
    song.g[G_DRMAP] = midi_set[7];
    song.g[G_CLKOUT] = midi_set[9];
    song.g[G_RMCH] = midi_set[8];
    layers_init();
    go_home();
    ui.force = 1;
}
void sim_btn(uint32_t label, uint32_t down)
{
    uint32_t bit;
    if (label >= NB) return;
    bit = 1u << panel.btn[label];
    if (down) { fm1_in.buttons |= bit; edges_btn |= bit; }
    else fm1_in.buttons &= ~bit;
}
void sim_key(uint32_t k, uint32_t down)
{
    if (k >= 27u) return;
    if (down) fm1_in.notes |= 1u << k; else fm1_in.notes &= ~(1u << k);
}
void sim_enc(uint32_t role, int32_t n) { if (role < NE) encs[panel.enc[role]] += n * panel.dir[role]; }
void sim_master(uint32_t v) { uint32_t k = v > 1023u ? 1023u : v; song.master_q12 = (k * k) >> 8; }
void sim_midi(uint32_t st, uint32_t d1, uint32_t d2)    /* comme usb.c range un paquet USB-MIDI */
{
    if (mi_w - mi_r >= MQ) return;
    if (st == 0xF8u || st == 0xFAu || st == 0xFBu || st == 0xFCu) midi_in_q[mi_w % MQ] = 0xFu | st << 8;
    else if (st >= 0x80u && st < 0xF0u) midi_in_q[mi_w % MQ] = (st >> 4) | st << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24;
    else return;
    mi_w++;
}
void sim_frame(void)
{
    fm1_ms += 16;
    ui_input();
    ui_leds();
    ui_draw();
}
void sim_render(uint32_t n)                       /* n multiple de CTL, flottants entrelacés dans sim_audio() */
{
    uint32_t f, i;
    if (n > 4096u) n = 4096u;
    for (f = 0; f + CTL <= n; f += CTL) {
        int32_t o[2 * CTL];
        mix_block(o, CTL);
        for (i = 0; i < CTL; i++) {
            if (i & 1u) { scope_bufr[scope_w & (SCOPE_N - 1u)] = vis_tap[2u * i + 1u]; scope_buf[scope_w++ & (SCOPE_N - 1u)] = vis_tap[2u * i]; }
            sim_out[2 * (f + i)] = (float)o[2 * i] * (1.0f / 32768.0f);
            sim_out[2 * (f + i) + 1] = (float)o[2 * i + 1] * (1.0f / 32768.0f);
        }
    }
}
float *sim_audio(void) { return sim_out; }
uint16_t *sim_fb(void) { return screen; }        /* l'ordre d'octets de la dalle (lcd_fill : swap16, lcd_blit) */
/* les LED dans le modèle Felucca de la page : [0] les boutons (PLAY : bit 14, le vert), [1] les touches, [2] [3] la
 * lueur (fm1_led_bg) des boutons et des touches, [6] le guide des touches (fm1_led_dim) */
uint32_t *sim_leds(void)
{
    uint32_t r, c, lb = 0, lk = 0, db = 0, dk = 0, gk = 0;
    for (r = 1; r < 5u; r++)
        for (c = 0; c < 16u; c++) {
            int id = MY_KEYMAP[r][c];
            uint32_t on, bg, dim;
            if (id < 0) continue;
            on = (fm1_led[c] >> r) & 1u; bg = (fm1_led_bg[c] >> r) & 1u; dim = (fm1_led_dim[c] >> r) & 1u;
            if (id >= 14) {
                if (on) lk |= 1u << (id - 14);
                if (bg) dk |= 1u << (id - 14);
                if (dim) gk |= 1u << (id - 14);
            } else {
                uint32_t label = panel_btn_of((uint32_t)id);
                if (label >= NB) continue;
                if (on) lb |= 1u << (label == B_PLAY ? 14u : label);
                if (bg) db |= 1u << label;
            }
        }
    sim_lights[0] = lb; sim_lights[1] = lk; sim_lights[2] = db; sim_lights[3] = dk;
    sim_lights[4] = 0; sim_lights[5] = 0; sim_lights[6] = 0; sim_lights[7] = gk;
    return sim_lights;
}
