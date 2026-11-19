"""Smoke tests for real loopback HTTP security; no model download required."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BRIDGE = Path(__file__).resolve().parents[1] / "src-tauri/resources/bridge.py"
ORIGIN = "https://tubedirector.com.br"

class HTTPContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = dict(os.environ, HOME=cls.tmp.name, USERPROFILE=cls.tmp.name, TD_TTS_SITE_ORIGIN=ORIGIN,
                   TD_TTS_PIPER_ONLY="1", TD_TTS_PORT=str(cls.port))
        cls.proc = subprocess.Popen([sys.executable, str(BRIDGE)], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(80):
            token = Path(cls.tmp.name, ".tubedirector-tts-token")
            if token.exists():
                cls.token = token.read_text().strip()
                try:
                    cls.response("/health", cls.token)
                    return
                except Exception:
                    pass
            time.sleep(.05)
        details = cls.proc.poll()
        if details is not None:
            stderr = cls.proc.stderr.read().decode("utf-8", "replace")
            raise RuntimeError(f"O servidor bridge terminou (code={details}): {stderr}")
        cls.proc.terminate()
        raise RuntimeError("O servidor bridge não iniciou: timeout de saúde")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
        cls.tmp.cleanup()

    @classmethod
    def response(cls, path, token, origin=ORIGIN, method="GET", body=None):
        headers = {"Origin":origin, "X-TD-Local-Token":token}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(cls.base+path, method=method, headers=headers, data=body)
        try:
            with urlopen(req,timeout=2) as r:
                return r.status, dict(r.headers), r.read()
        except HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_health_good_token(self):
        code,headers,body = self.response("/health",self.token)
        self.assertEqual(code,200)
        self.assertTrue(json.loads(body)["ok"])
        self.assertEqual(headers.get("Access-Control-Allow-Origin"),ORIGIN)

    def test_health_bad_token(self):
        code,_,_ = self.response("/health","not-authorized")
        self.assertEqual(code,403)

    def test_health_bad_origin(self):
        code,headers,_ = self.response("/health",self.token,"https://malicious.example")
        self.assertEqual(code,403)
        self.assertNotIn("Access-Control-Allow-Origin",headers)

    def test_generation_requires_billing_ticket(self):
        body=json.dumps({"text":"Teste","speaker":"piper_cadu","language":"Portuguese"}).encode()
        code,_,data = self.response("/jobs",self.token,method="POST",body=body)
        self.assertEqual(code,403)
        self.assertIn("assinatura",json.loads(data)["error"])
