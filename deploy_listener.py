"""
GitHub webhook listener for fejoh-site.

Verifies HMAC-SHA256 against DEPLOY_SECRET. On push to the target branch
runs `git fetch && git reset --hard origin/<branch>` inside the repo
directory. Since nginx serves the same directory via a read-only mount,
the new files are live immediately — no rebuild required.

Listens on :9000. Caddy fronts it at https://fejoh.com/__deploy.
"""
import hashlib
import hmac
import http.server
import json
import os
import subprocess
import threading
import time

SECRET   = os.environ.get("DEPLOY_SECRET", "").encode()
REPO_DIR = os.environ.get("REPO_DIR", "/repo")
BRANCH   = os.environ.get("GIT_BRANCH", "main")
PORT     = int(os.environ.get("PORT", "9000"))

_lock = threading.Lock()
_last_run = 0.0

def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()

def _deploy_blocking():
    for cmd in (
        ["git", "fetch", "origin", BRANCH],
        ["git", "reset", "--hard", f"origin/{BRANCH}"],
        ["git", "clean", "-fd"],
    ):
        rc, out = run(cmd, cwd=REPO_DIR)
        if rc != 0:
            print("[deploy] FAILED step:", cmd, flush=True)
            print("[deploy]", out, flush=True)
            return
    print("[deploy] OK", flush=True)

def deploy_async():
    global _last_run
    with _lock:
        now = time.time()
        if now - _last_run < 5:
            return "rate-limited"
        _last_run = now
    threading.Thread(target=_deploy_blocking, daemon=True).start()
    return "queued"

class Handler(http.server.BaseHTTPRequestHandler):
    def _reply(self, code, body=""):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            return self._reply(200, "ok\n")
        return self._reply(404, "")

    def do_POST(self):
        if self.path not in ("/", "/deploy", "/__deploy"):
            return self._reply(404, "")
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(n) if n else b""
        except Exception:
            return self._reply(400, "bad body")
        sig = self.headers.get("X-Hub-Signature-256", "")
        if not SECRET:
            return self._reply(500, "server misconfigured: no secret")
        expected = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return self._reply(401, "bad signature")
        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            return self._reply(200, "pong")
        if event != "push":
            return self._reply(200, f"ignored event: {event}")
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            return self._reply(400, "bad json")
        ref = payload.get("ref", "")
        if ref != f"refs/heads/{BRANCH}":
            return self._reply(200, f"ignored ref: {ref}")
        return self._reply(202, deploy_async() + "\n")

    def log_message(self, fmt, *args):
        print("[deploy]", self.address_string(), fmt % args, flush=True)

if __name__ == "__main__":
    print(f"deploy listener on :{PORT} repo={REPO_DIR} branch={BRANCH}", flush=True)
    http.server.ThreadingHTTPServer(("", PORT), Handler).serve_forever()
