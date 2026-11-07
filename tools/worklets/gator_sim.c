/* SPDX-License-Identifier: GPL-3.0-only
 * GATOR (npi3pak/fm1-gator, GPL-3.0) pour le panneau : son simulateur d'hôte (host/sim.c, inchangé : le code de
 * l'appli sur un HAL de bouchons), mené comme main.c mène l'appareil : une image toutes les 15 ms (fw_input_read,
 * app_frame), le son par blocs de FW_BLOCK (app_audio). Compilé à 44,1 kHz (FW_FS48=0, la famille que son
 * build sait faire), le rythme de la page. Ses deux emplacements de mémoire (fw_store) sont gardés par la page. */
#define main gator_sim_main
#include "sim.c"
#undef main

static float sim_out[2u * FW_BLOCK];
static uint32_t sim_lights[8];

void sim_init(void) { lcd_init(); app_init(); }
uint8_t *sim_store(void) { return &host_store[0][0]; }
uint32_t *sim_store_len(void) { return host_store_len; }
uint32_t sim_store_size(void) { return FW_STORE_SLOTS * FW_STORE_MAX; }
uint32_t sim_block(void) { return FW_BLOCK; }

void sim_btn(uint32_t label, uint32_t down) { if (label < FW_BTN_COUNT) host_button((int)label, (int)down); }
void sim_key(uint32_t k, uint32_t down) { if (k < FW_KEYS) host_key(k, (int)down); }
void sim_enc(uint32_t role, int32_t n) { if (role < FW_KNOB_COUNT) fm1_in.enc_steps[FW_KNOB_MATRIX[role]] += (int16_t)n; }
void sim_master(uint32_t v) { host_adc_master = v > 1023u ? 1023 : (int32_t)v; }
void sim_midi(uint32_t st, uint32_t d1, uint32_t d2) { if (st >= 0x80u) host_midi(st, d1 & 127u, d2 & 127u); }

void sim_frame(void)
{
    fw_input_t in;
    fm1_ms += 15u;
    fw_input_read(&in);
    app_frame(&in);
}

/* un bloc de FW_BLOCK échantillons stéréo, flottants entrelacés */
float *sim_render(void)
{
    int32_t block[2u * FW_BLOCK];
    uint32_t i;
    app_audio(block, FW_BLOCK);
    for (i = 0; i < 2u * FW_BLOCK; i++) sim_out[i] = (float)block[i] * (1.0f / 32768.0f);
    return sim_out;
}
uint16_t *sim_fb(void) { return host_fb; }      /* RGB565 dans l'ordre de la machine */

/* les LED dans le modèle Felucca de la page : [0] les boutons dans l'ordre du panneau (PLAY : bit 14, le vert),
 * [1] les touches */
uint32_t *sim_leds(void)
{
    uint32_t b, lb = 0;
    for (b = 0; b < FW_BTN_COUNT; b++)
        if ((host_leds >> FW_BTN_MATRIX[b]) & 1u) lb |= 1u << (b == FW_BTN_PLAY ? 14u : b);
    sim_lights[0] = lb;
    sim_lights[1] = (uint32_t)(host_leds >> 14) & 0x7FFFFFFu;
    return sim_lights;
}
