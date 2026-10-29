/* emscripten.h de remplacement : pour compiler sans Emscripten un firmware dont la page tourne sous Emscripten
 * (tools/worklets/asyncify.sh). Ses deux fonctions deviennent des importations que notre worklet fournit :
 * emscripten_get_now, l'heure ; emscripten_sleep, la main rendue (Asyncify en fait une coroutine). */
#pragma once
#define EMSCRIPTEN_KEEPALIVE __attribute__((used, visibility("default")))
__attribute__((import_module("env"), import_name("emscripten_get_now"))) double emscripten_get_now(void);
__attribute__((import_module("env"), import_name("emscripten_sleep"))) void emscripten_sleep(unsigned int ms);
