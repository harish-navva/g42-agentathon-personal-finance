"""
Static UI server for the Personal Finance Agent.

Serves index.html, styles.css, app.js from the ui/ folder on port 8001
(per hackathon rules: API on 8000, UI on 8001).

Usage:
    python ui/server.py
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8001

# Serve files from this script's directory (ui/)
UI_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(UI_DIR)


class UIRequestHandler(SimpleHTTPRequestHandler):
    """Adds no-cache headers so the user sees their changes immediately."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        # Quieter than default
        sys.stdout.write(f"[ui]  {self.address_string()} - {format % args}\n")


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"")
    print(f"  ╭───────────────────────────────────────────────╮")
    print(f"  │  Karim's Money - UI                          │")
    print(f"  │                                               │")
    print(f"  │  Open in browser: {url:<26}│")
    print(f"  │                                               │")
    print(f"  │  Backend API expected on port 8000.           │")
    print(f"  │  Start it in another terminal: python run.py │")
    print(f"  ╰───────────────────────────────────────────────╯")
    print(f"")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server = HTTPServer(("0.0.0.0", PORT), UIRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[ui]  Shutting down (Ctrl+C)…")
    finally:
        server.server_close()
