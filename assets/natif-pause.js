// Fm1 : la pause des firmwares natifs quittés. La page garde leur worklet (et donc leur état) quand on change de
// firmware ; sans pause, il continuerait de calculer et d'envoyer son écran à la page. Chargé avant tout firmware natif
// dans le même AudioWorklet, il donne à chaque processeur enregistré ensuite un paramètre fm1Pause : à 1, process ne fait
// plus rien (la mémoire du firmware reste telle quelle), à 0 il reprend.
const register = globalThis.registerProcessor;
globalThis.registerProcessor = (name, Processor) => register(name, class extends Processor {
  static get parameterDescriptors() {
    return [...(super.parameterDescriptors || []), { name: "fm1Pause", defaultValue: 0, minValue: 0, maxValue: 1, automationRate: "k-rate" }];
  }
  process(inputs, outputs, parameters) {
    if (parameters.fm1Pause && parameters.fm1Pause[0] >= 0.5) return true;
    return super.process(inputs, outputs, parameters);
  }
});
