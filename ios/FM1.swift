// FM-1 pour iPad : le site (dossier www, assemblé par l'action GitHub iPad) dans une WKWebView, servi par
// le schéma fm1://localhost. La page y est un contexte sécurisé (AudioWorklet, modules, WebAssembly) comme
// sur GitHub Pages, et garde sa mémoire (localStorage, IndexedDB) dans l'app.
import AVFoundation
import CoreMIDI
import UIKit
import WebKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        try? AVAudioSession.sharedInstance().setCategory(.playback)   // le son, même en mode silencieux
        return true
    }
}

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        window = UIWindow(windowScene: scene)
        window?.rootViewController = FM1ViewController()
        window?.makeKeyAndVisible()
    }
}

final class FM1ViewController: UIViewController, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private var saved: URL?             // le fichier de « Sauvegarder », le temps de l'écrire
    private var diagnosed = false

    override var prefersStatusBarHidden: Bool { true }
    override var prefersHomeIndicatorAutoHidden: Bool { true }

    override func loadView() {
        let config = WKWebViewConfiguration()
        config.setURLSchemeHandler(BundleFiles(), forURLScheme: "fm1")
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        // déjà sans navigateur, comme ouverte depuis l'écran d'accueil : la page n'offre pas le plein écran
        config.userContentController.addUserScript(WKUserScript(
            source: "Object.defineProperty(navigator, 'standalone', { value: true })",
            injectionTime: .atDocumentStart, forMainFrameOnly: false))
        // le Web MIDI de la page, sur le MIDI de l'iPad (midi.js, MIDIBridge)
        let midi = MIDIBridge()
        config.userContentController.addScriptMessageHandler(midi, contentWorld: .page, name: "fm1midi")
        config.userContentController.addUserScript(WKUserScript(
            source: try! String(contentsOf: Bundle.main.url(forResource: "midi", withExtension: "js")!, encoding: .utf8),
            injectionTime: .atDocumentStart, forMainFrameOnly: false))
        let web = WKWebView(frame: .zero, configuration: config)
        midi.web = web
        web.navigationDelegate = self
        web.uiDelegate = self
        web.isOpaque = false
        web.backgroundColor = UIColor(named: "Fond")
        web.scrollView.contentInsetAdjustmentBehavior = .never   // la page place ses marges (safe-area-inset)
        if #available(iOS 16.4, *) { web.isInspectable = true }   // Safari > Développement, depuis un Mac
        web.load(URLRequest(url: URL(string: "fm1://localhost/index.html")!))
        view = web
    }

    // un lien vers le Web s'ouvre dans Safari ; « Sauvegarder » (un lien download) devient un fichier
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if action.shouldPerformDownload { return decisionHandler(.download) }
        if let url = action.request.url, url.scheme == "http" || url.scheme == "https" {
            UIApplication.shared.open(url)
            return decisionHandler(.cancel)
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(suggestedFilename)
        try? FileManager.default.removeItem(at: url)
        saved = url
        completionHandler(url)
    }

    // le fichier écrit, l'iPad demande où le ranger (Fichiers, iCloud Drive)
    func downloadDidFinish(_ download: WKDownload) {
        guard let url = saved else { return }
        present(UIDocumentPickerViewController(forExporting: [url], asCopy: true), animated: true)
    }

    // window.confirm, que demande la restauration d'une sauvegarde
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let fr = Locale.preferredLanguages.first?.hasPrefix("fr") ?? false
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: fr ? "Annuler" : "Cancel", style: .cancel) { _ in completionHandler(false) })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler(true) })
        present(alert, animated: true)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        webView.reload()
    }

    // la vérification dans le simulateur (action GitHub iPad) : FM1_DIAGNOSTIC, un corps de fonction
    // JavaScript, s'exécute une fois la page chargée ; son résultat va dans Documents/diagnostic.txt
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard !diagnosed, let js = ProcessInfo.processInfo.environment["FM1_DIAGNOSTIC"] else { return }
        diagnosed = true
        webView.callAsyncJavaScript(js, arguments: [:], in: nil, in: .page) { result in
            let text: String
            switch result {
            case .success(let value): text = "\(value)"
            case .failure(let error): text = "\(error)"
            }
            let out = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("diagnostic.txt")
            try? text.write(to: out, atomically: true, encoding: .utf8)
        }
    }
}

// le MIDI de l'iPad pour la page (midi.js) : chaque source CoreMIDI (un clavier USB) est une entrée ; ses octets
// vont à __fm1midi.rx, la liste des appareils à __fm1midi.ports, dans la page principale
final class MIDIBridge: NSObject, WKScriptMessageHandlerWithReply {
    weak var web: WKWebView?
    private var client = MIDIClientRef()
    private var input = MIDIPortRef()
    private var linked = Set<MIDIUniqueID>()

    // « ouvrir », la première demande de la page : CoreMIDI s'ouvre ; la réponse est la liste des appareils
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage, replyHandler: @escaping (Any?, String?) -> Void) {
        if client == 0 {
            MIDIClientCreateWithBlock("FM-1" as CFString, &client) { [weak self] _ in
                DispatchQueue.main.async { self?.post() }      // un appareil branché ou débranché
            }
            MIDIInputPortCreateWithBlock(client, "FM-1" as CFString, &input) { [weak self] list, source in
                let id = Int(bitPattern: source)                // l'identifiant de la source, donné à MIDIPortConnectSource
                let offset = MemoryLayout<MIDIPacket>.offset(of: \MIDIPacket.data)!
                var bytes = [UInt8]()
                for packet in list.unsafeSequence() {
                    bytes += UnsafeRawBufferPointer(start: UnsafeRawPointer(packet) + offset, count: Int(packet.pointee.length))
                }
                let js = "window.__fm1midi && __fm1midi.rx('\(id)', [\(bytes.map { String($0) }.joined(separator: ","))])"
                DispatchQueue.main.async { self?.web?.evaluateJavaScript(js) }
            }
        }
        replyHandler(ports(), nil)
    }

    // les sources présentes, [[id, nom]] ; une source nouvelle est reliée au port d'entrée
    private func ports() -> [[String]] {
        var list = [[String]](), here = Set<MIDIUniqueID>()
        for i in 0..<MIDIGetNumberOfSources() {
            let source = MIDIGetSource(i)
            var id: MIDIUniqueID = 0
            var name: Unmanaged<CFString>?
            MIDIObjectGetIntegerProperty(source, kMIDIPropertyUniqueID, &id)
            MIDIObjectGetStringProperty(source, kMIDIPropertyDisplayName, &name)
            if !linked.contains(id) { MIDIPortConnectSource(input, source, UnsafeMutableRawPointer(bitPattern: Int(id))) }
            here.insert(id)
            list.append([String(id), (name?.takeRetainedValue() as String?) ?? "MIDI"])
        }
        linked = here
        return list
    }

    private func post() {
        guard let json = try? JSONSerialization.data(withJSONObject: ports()), let list = String(data: json, encoding: .utf8) else { return }
        web?.evaluateJavaScript("window.__fm1midi && __fm1midi.ports(\(list))")
    }
}

// les fichiers du site, lus dans le dossier www de l'app ; un fichier absent répond 404, comme sur GitHub Pages
final class BundleFiles: NSObject, WKURLSchemeHandler {
    private let root = Bundle.main.bundleURL.appendingPathComponent("www", isDirectory: true).standardizedFileURL
    private let types = [
        "html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8", "mjs": "text/javascript; charset=utf-8",
        "json": "application/json; charset=utf-8", "txt": "text/plain; charset=utf-8", "css": "text/css; charset=utf-8",
        "wasm": "application/wasm", "png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml",
    ]

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        let path = url.path.isEmpty || url.path.hasSuffix("/") ? url.path + "index.html" : url.path
        let file = root.appendingPathComponent(path).standardizedFileURL
        guard file.path.hasPrefix(root.path + "/"), let data = try? Data(contentsOf: file, options: .mappedIfSafe) else {
            task.didReceive(HTTPURLResponse(url: url, statusCode: 404, httpVersion: nil, headerFields: nil)!)
            task.didFinish()
            return
        }
        let type = types[file.pathExtension.lowercased()] ?? "application/octet-stream"
        task.didReceive(HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type": type, "Content-Length": "\(data.count)"])!)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}
