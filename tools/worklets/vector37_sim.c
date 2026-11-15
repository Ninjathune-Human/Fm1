/* SPDX-License-Identifier: GPL-3.0-only
 * VECTOR37 (genkigenki/Vector37, GPL-3.0) pour le panneau : sa version FM-1 (BOARD=fm1, firmware/src/panel_fm1.c), sur
 * le FM-1 simulé de ses tests d'hôte (tests/panel.h avec BOARD_SMK37 0, inchangé, celui de tests/fm1_panel.c). Son
 * simulateur web (web/sim) est celui du SMK-37 : pads, faders, molettes. panel_render est l'horloge de l'appareil : le
 * son, et la boucle principale (entrées, LED, écran) toutes les 15 ms. Rien n'est gardé : sur le FM-1, VECTOR37 n'a pas
 * de mémoire à lui. */
#define BOARD_SMK37 0
#include "panel.h"

static float sim_l[1024], sim_r[1024];
static uint32_t sim_lights[8];

void sim_init(void) { panel_init(); }
void sim_render(uint32_t n) { panel_render(sim_l, sim_r, n > 1024u ? 1024u : n); }
float *sim_out_l(void) { return sim_l; }
float *sim_out_r(void) { return sim_r; }
uint16_t *sim_fb(void) { return fb; }            /* RGB565 dans l'ordre de la machine (lcd_blit le remet à l'endroit) */

/* le panneau : ses boutons dans son ordre (FX 0 .. REC 11, OCT- 12, OCT+ 13), ceux du FM-1 dans celui de sa matrice
 * (OCT- 0, OCT+ 1, FX 2 .. REC 13) ; ses molettes SELECT 0, ALGORITHM 1, PRESETS 2, KNOB 1 à 4 de 3 à 6, celles du
 * FM-1 SELECT 0, ALGORITHM 1, KNOB 1 à 4 de 2 à 5, PRESETS 6 */
static const uint8_t ENC_OF_ROLE[7] = {0, 1, 6, 2, 3, 4, 5};
void sim_btn(uint32_t label, uint32_t down) { if (label < 14u) panel_button((label + 2u) % 14u, down); }
void sim_key(uint32_t k, uint32_t down) { panel_note(k, down); }
void sim_enc(uint32_t role, int32_t n) { if (role < 7u) panel_enc(ENC_OF_ROLE[role], n); }
void sim_master(uint32_t v) { panel_pot = v > 1023u ? 1023 : (int32_t)v; }
void sim_midi(uint32_t st, uint32_t d1, uint32_t d2) { if (st >= 0x80u) panel_midi(st, d1 & 127u, d2 & 127u); }

/* les LED dans le modèle Felucca de la page : [0] les boutons allumés dans son ordre (PLAY : bit 14, le vert), [1] les
 * touches, [2] [3] la lueur des boutons et des touches (led_lvl : 0 éteint, 1 la lueur, 2 allumé) */
uint32_t *sim_leds(void)
{
    uint32_t id, lb = 0, lk = 0, gb = 0, gk = 0;
    for (id = 0; id < 41u; id++) {
        uint32_t lvl = led_lvl[id];
        if (!lvl) continue;
        if (id >= 14u) {
            if (lvl == 2u) lk |= 1u << (id - 14u); else gk |= 1u << (id - 14u);
        } else {
            uint32_t label = (id + 12u) % 14u;
            if (lvl == 2u) lb |= 1u << (label == 10u ? 14u : label); else gb |= 1u << label;
        }
    }
    sim_lights[0] = lb; sim_lights[1] = lk; sim_lights[2] = gb; sim_lights[3] = gk;
    return sim_lights;
}
