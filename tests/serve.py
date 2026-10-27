"""Serveur HTTP local pour les tests Playwright."""
import contextlib
import functools
import http.server
import threading


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".js": "text/javascript", ".mjs": "text/javascript"}

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def serve(root):
    """Sert `root` sur un port libre de 127.0.0.1 ; renvoie l'URL de base, terminée par /."""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Handler, directory=root))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    finally:
        httpd.shutdown()
        httpd.server_close()
