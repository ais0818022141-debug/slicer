"""
TealMED Notes Studio Launcher
==============================
Launches the interactive Clinical Notes Studio web application in your default browser.

Usage:
  python notes/run_studio.py
  python run_studio.py
"""

import sys
import os
import webbrowser
import http.server
import socketserver
import socket
from pathlib import Path


def find_free_port(start_port=8080, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start_port


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    notes_dir = Path(__file__).resolve().parent
    os.chdir(notes_dir)

    port = find_free_port(8080)
    url = f"http://localhost:{port}/notes_studio.html"

    print("=" * 68)
    print(" 🩺 TealMED Clinical Notes Studio (Web UI)")
    print("=" * 68)
    print(f" Serving directory : {notes_dir}")
    print(f" Opening in browser: {url}")
    print("=" * 68)
    print(" Press Ctrl+C in this terminal to stop the server.\n")

    webbrowser.open(url)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Notes Studio server. Bye!")


if __name__ == "__main__":
    main()
