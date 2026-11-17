// FM-1 pour iPad : le site (dossier www, assemblé par l'action GitHub iPad) dans une WKWebView, servi par
// le schéma fm1://localhost. La page y est un contexte sécurisé (AudioWorklet, modules, WebAssembly) comme
// sur GitHub Pages, et garde sa mémoire (localStorage, IndexedDB) dans l'app.
import AVFoundation
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
        let web = WKWebView(frame: .zero, configuration: config)
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
