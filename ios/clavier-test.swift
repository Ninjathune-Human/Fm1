// Un clavier MIDI virtuel sur le Mac de l'action iPad : la source « Clavier test » joue un do (note 60) toutes
// les demi-secondes pendant deux minutes ; la vérification (diagnostic.js) regarde s'il arrive dans la page.
import CoreMIDI
import Foundation

var client = MIDIClientRef(), source = MIDIEndpointRef()
MIDIClientCreateWithBlock("Clavier test" as CFString, &client, nil)
MIDISourceCreate(client, "Clavier test" as CFString, &source)
print("Clavier test prêt")
for _ in 0..<240 {
    var list = MIDIPacketList()
    let packet = MIDIPacketListInit(&list)
    MIDIPacketListAdd(&list, MemoryLayout<MIDIPacketList>.size, packet, 0, 3, [0x90, 60, 100])
    MIDIReceived(source, &list)
    Thread.sleep(forTimeInterval: 0.5)
}
