/* SPDX-License-Identifier: GPL-3.0-only
 * Melodee (keremimo/melodee, GPL-3.0) pour le panneau. Son test d'interface (tests/ui_test.c, inchangé) assemble
 * déjà le firmware sur l'hôte : le son de hostsim.c et l'interface de firmware/src/ui*.c, sur des bouchons
 * d'affichage, de boutons, de touches et de molettes. On le mène comme main.c mène l'appareil : une image d'interface
 * toutes les 16 ms (ui_input, ui_leds, ui_draw), le son par blocs de CTL échantillons (mix_block, comme audio.c).
 * Le MIDI entre comme usb.c range un paquet USB-MIDI. Pas de mémoire flash : rien n'est gardé d'une session à l'autre. */
#define main melodee_ui_tests
#include "ui_test.c"
#undef main

/* la matrice de l'appareil (hal/fm1_input.h), qui complète la déclaration vide du test : les LED retrouvent leur place */
#include "sim_keymap.h"

static float sim_out[2 * 4096];
static uint32_t sim_lights[8];

void sim_init(void)
{
    fm6_init();                                   /* comme melodee_init (main.c) */
    cz_init();
    ui_power_on();
    settings.magic = 0;
    settings_init();                              /* NIGHT, la palette par défaut */
    settings_lights = LIGHTS_MID;
    song.master_q12 = 2048;
    screen_clear();
    ui.home = 1;
    ui.force = 1;
}

/* label : l'ordre du panneau (panel.c B_FX .. B_OCTUP, celui de la page) */
void sim_btn(uint32_t label, uint32_t down)
{
    uint32_t bit;
    if (label >= NB) return;
    bit = 1u << panel.btn[label];
    if (down) { fm1_in.buttons |= bit; host_pressed |= bit; }
    else fm1_in.buttons &= ~bit;
}
void sim_key(uint32_t k, uint32_t down)
{
    if (k >= 27u) return;
    if (down) { fm1_in.notes |= 1u << k; host_notes |= 1u << k; }
    else fm1_in.notes &= ~(1u << k);
}
void sim_enc(uint32_t role, int32_t n)
{
    if (role >= NE) return;
    host_enc[panel.enc[role]] += n * panel.dir[role];
}
void sim_master(uint32_t v)                       /* 0..1023, comme le potentiomètre (main.c) */
{
    uint32_t k = v > 1023u ? 1023u : v;
    midi_master_physical((k * k) >> 8);
}
uint32_t sim_midi(uint32_t st, uint32_t d1, uint32_t d2)
{
    if (st == 0xF8u || st == 0xFAu || st == 0xFBu || st == 0xFCu)
        return (uint32_t)midi_enqueue(0xFu | st << 8, 1u);
    if (st < 0x80u || st >= 0xF0u)
        return 1u;
    return (uint32_t)midi_enqueue((st >> 4) | st << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24, 1u);
}

/* une image : 16 ms de l'appareil */
void sim_frame(void)
{
    host_ticks += 16000u;
    fm1_ms += 16u;
    ui_input();
    ui_leds();
    ui_draw();
}

/* n échantillons stéréo (n multiple de CTL), flottants entrelacés dans sim_audio() */
void sim_render(uint32_t n)
{
    uint32_t f, i;
    if (n > 4096u) n = 4096u;
    for (f = 0; f + CTL <= n; f += CTL) {
        int32_t o[2 * CTL];
        mix_block(o, CTL);
        for (i = 0; i < CTL; i++) {
            int32_t l = o[2 * i], r = o[2 * i + 1];
            if (i & 1u) scope_buf[scope_w++ & (SCOPE_N - 1u)] = (int16_t)(l > 32767 ? 32767 : l < -32768 ? -32768 : l);
            sim_out[2 * (f + i)] = (float)l * (1.0f / 32768.0f);
            sim_out[2 * (f + i) + 1] = (float)r * (1.0f / 32768.0f);
        }
    }
}
float *sim_audio(void) { return sim_out; }
uint16_t *sim_fb(void) { return host_screen; }   /* l'ordre d'octets de la dalle (lcd_fill, lcd_blit) */

/* les LED dans le modèle Felucca de la page : [0] les boutons dans l'ordre du panneau (PLAY allumé : bit 14, le vert),
 * [1] les touches, [2] [3] la lueur de repos des boutons et des touches, [5] [6] ce qui respire */
uint32_t *sim_leds(void)
{
    uint32_t r, c, lb = 0, lk = 0, db = 0, dk = 0, bb = 0, bk = 0;
    for (r = 0; r < 6u; r++)
        for (c = 0; c < FM1_NCOL; c++) {
            int id = FM1_KEYMAP[r][c];
            uint32_t on, dim, br, bit;
            if (id < 0) continue;
            on = (fm1_led[c] >> r) & 1u;
            dim = ((fm1_led_dim[0][c] >> r) & 1u && fm1_led_dim_mask[0]) || ((fm1_led_dim[1][c] >> r) & 1u);
            br = (fm1_led_dim[2][c] >> r) & 1u;
            if (id >= 14) {
                bit = 1u << (id - 14);
                if (on) lk |= bit;
                if (dim) dk |= bit;
                if (br) bk |= bit;
            } else {
                uint32_t label = panel_btn_of((uint32_t)id);
                if (label >= NB) continue;
                bit = 1u << (label == B_PLAY ? 14u : label);
                if (on) lb |= bit;
                if (dim) db |= 1u << label;
                if (br) bb |= 1u << label;
            }
        }
    sim_lights[0] = lb; sim_lights[1] = lk; sim_lights[2] = db; sim_lights[3] = dk;
    sim_lights[4] = 0; sim_lights[5] = bb; sim_lights[6] = bk; sim_lights[7] = 0;
    return sim_lights;
}
