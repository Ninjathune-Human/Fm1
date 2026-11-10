/* SPDX-License-Identifier: GPL-3.0-only
 * Hortator (deadactive/hortator, GPL-3.0) pour le panneau : son simulateur (tests/sim_core.c, inchangé) et une
 * entrée MIDI, que sa page n'a pas. Un message arrive comme usb_app8.c range un paquet USB-MIDI : l'horloge et
 * Start / Continue / Stop en code 0xF, les messages de canal sur leur propre code. */
#include "sim_core.c"

uint32_t sim_midi(uint32_t st, uint32_t d1, uint32_t d2)
{
    if (st == 0xF8u || st == 0xFAu || st == 0xFBu || st == 0xFCu)
        return (uint32_t)midi_enqueue(0xFu | st << 8, 1u);
    if (st < 0x80u || st >= 0xF0u)
        return 1u;
    return (uint32_t)midi_enqueue((st >> 4) | st << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24, 1u);
}

/* Les couches de led_dim.c (la lueur, le niveau moyen, la respiration), que le panneau dessine à leur part du temps
 * allumé : elles n'existent que lorsque led_dim_on (sinon fm1_led seul, comme avant). [0] [1] boutons et touches
 * allumés (sans ce qui respire, que sim_leds compte comme allumé), [2] [3] dans la lueur, [4] [5] au niveau moyen,
 * [6] [7] qui respirent ; [8] la part de la lueur, [9] celle du niveau moyen, en dix-millièmes de l'allumé (une
 * colonne allumée un tick de 100 µs) : Hortator, une impulsion de led_glow_w ; MNM-1, des images sur 20 (led_glow_ph) */
static uint32_t sim_lay_w[10];
static uint32_t sim_lay_bit(uint32_t id, uint32_t sh)
{
    uint32_t p, r;
    for (p = 0; p < FM1_NCOL; p++)
        for (r = 1; r < 5u; r++)
            if (FM1_KEYMAP[r][p] == (int8_t)id)
                return ((led_dim_on ? led_lay[p] : sh ? 0u : (uint32_t)fm1_led[p]) >> (sh + r)) & 1u;
    return 0;
}
static uint32_t sim_frames20(uint32_t m)
{
    uint32_t f, n = 0;
    for (f = 0; f < 20u; f++)
        n += (m >> f) & 1u;
    return n * 10000u / 20u;
}
uint32_t *sim_layers(void)
{
    uint32_t i, b, k;
    for (i = 0; i < 4u; i++) {                       /* 0 l'allumé, 8 le milieu, 16 la lueur, 24 la respiration */
        uint32_t sh = i * 8u, mb = 0, mk = 0, w = i == 0 ? 0u : i == 1 ? 4u : i == 2 ? 2u : 6u;
        for (b = 0; b < NB; b++)
            mb |= sim_lay_bit(panel.btn[b], sh) << b;
        for (k = 0; k < 27u; k++)
            mk |= sim_lay_bit(14u + k, sh) << k;
        sim_lay_w[w] = mb;
        sim_lay_w[w + 1u] = mk;
    }
#ifdef LED_GLOW_LO
    sim_lay_w[8] = led_glow_w * 100u / FM1_TICKS_PER_US;
#else
    sim_lay_w[8] = sim_frames20(led_glow_ph);
#endif
    sim_lay_w[9] = sim_frames20(led_mid_ph);
    return sim_lay_w;
}
