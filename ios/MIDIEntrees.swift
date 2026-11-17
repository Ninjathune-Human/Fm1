// Les entrées MIDI de l'appareil (un clavier USB) : chaque source CoreMIDI est reliée à un port d'entrée ; ses
// octets vont à recu (sur un fil de CoreMIDI), un appareil branché ou débranché appelle change. Sans WebKit :
// l'action iPad l'essaie aussi sur le Mac (clavier-test.swift), avec une source virtuelle.
import CoreMIDI

final class MIDIEntrees {
    private var client = MIDIClientRef()
    private var port = MIDIPortRef()
    private var linked = Set<MIDIUniqueID>()

    init(recu: @escaping (String, [UInt8]) -> Void, change: @escaping () -> Void) {
        MIDIClientCreateWithBlock("FM-1" as CFString, &client) { _ in change() }
        MIDIInputPortCreateWithBlock(client, "FM-1" as CFString, &port) { list, source in
            let offset = MemoryLayout<MIDIPacket>.offset(of: \MIDIPacket.data)!
            var bytes = [UInt8]()
            for packet in list.unsafeSequence() {
                bytes += UnsafeRawBufferPointer(start: UnsafeRawPointer(packet) + offset, count: Int(packet.pointee.length))
            }
            recu(String(Int(bitPattern: source)), bytes)   // l'identifiant donné à MIDIPortConnectSource
        }
    }

    // les sources présentes, [[id, nom]] ; une source nouvelle est reliée au port d'entrée
    func sources() -> [[String]] {
        var list = [[String]](), here = Set<MIDIUniqueID>()
        for i in 0..<MIDIGetNumberOfSources() {
            let source = MIDIGetSource(i)
            var id: MIDIUniqueID = 0
            var name: Unmanaged<CFString>?
            MIDIObjectGetIntegerProperty(source, kMIDIPropertyUniqueID, &id)
            MIDIObjectGetStringProperty(source, kMIDIPropertyDisplayName, &name)
            if !linked.contains(id) { MIDIPortConnectSource(port, source, UnsafeMutableRawPointer(bitPattern: Int(id))) }
            here.insert(id)
            list.append([String(id), (name?.takeRetainedValue() as String?) ?? "MIDI"])
        }
        linked = here
        return list
    }
}
