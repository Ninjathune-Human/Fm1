// L'essai de MIDIEntrees sur le Mac de l'action iPad (même API CoreMIDI que l'iPad, dont le simulateur n'accepte
// pas de source virtuelle hors d'une app) : la source « Clavier test » envoie une note puis un SysEx de 300 octets,
// plus long qu'un MIDIPacket ; ils doivent arriver intacts, avec l'identifiant que donne sources().
import CoreMIDI
import Foundation

@main
enum ClavierTest {
    static func main() {
        var client = MIDIClientRef(), source = MIDIEndpointRef()
        MIDIClientCreateWithBlock("Clavier test" as CFString, &client, nil)
        MIDISourceCreate(client, "Clavier test" as CFString, &source)
        let note: [UInt8] = [0x90, 60, 100], sysex: [UInt8] = [0xF0] + (0..<298).map { UInt8($0 % 128) } + [0xF7]
        var got = [UInt8](), ids = Set<String>()
        let fin = DispatchSemaphore(value: 0)
        let entrees = MIDIEntrees(recu: { id, bytes in
            ids.insert(id); got += bytes
            if got.count >= note.count + sysex.count { fin.signal() }
        }, change: {})
        guard let id = entrees.sources().first(where: { $0[1] == "Clavier test" })?[0] else {
            print("Clavier test absent des sources"); exit(1)
        }
        Thread.sleep(forTimeInterval: 0.5)
        for message in [note, sysex] {
            let buffer = UnsafeMutableRawPointer.allocate(byteCount: 1024, alignment: 8)
            let list = buffer.bindMemory(to: MIDIPacketList.self, capacity: 1)
            MIDIPacketListAdd(list, 1024, MIDIPacketListInit(list), 0, message.count, message)
            MIDIReceived(source, list)
            buffer.deallocate()
        }
        let attendu = fin.wait(timeout: .now() + 5) == .success && got == note + sysex && ids == [id]
        print("\(attendu ? "ok" : "échec") : \(got.count) octets reçus sur \(note.count + sysex.count), de \(ids.sorted()) (Clavier test : \(id))")
        exit(attendu ? 0 : 1)
    }
}
