"""Independent executable checks, run after a subject finishes.

SUBJECT points at a frozen checkout. Only temporary fixture/configuration
directories are written. This module is never copied into subject checkouts.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest


DEPLOYMENTS = [{"name": "example", "sourceManifest": "a" * 200}]


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1alpha/deployments":
            self.send_error(404)
            return
        body = json.dumps({"deployments": DEPLOYMENTS}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class ExecutableOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subject = Path(os.environ["SUBJECT"])
        cls.config = tempfile.TemporaryDirectory(prefix="fm124-acceptance-")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.address = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.worker.join()
        cls.server.server_close()
        cls.config.cleanup()

    def run_cli(self, args, ci, columns="20"):
        env = dict(os.environ, CI=ci, NO_COLOR="1", COLUMNS=columns)
        for key in ("FORCE_COLOR", "DEBUG", "OCM_RM_CA_FILE"):
            env.pop(key, None)
        result = subprocess.run([
            "node", str(self.subject / "client/cli/bin/fleetctl"),
            "--config-dir", self.config.name, *args,
        ], env=env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result

    def check_data(self, ci):
        result = self.run_cli(["deployment", "list", "--server", self.address,
                               "--output", "json"], ci)
        self.assertEqual(result.stdout, (json.dumps(DEPLOYMENTS, indent=2) + "\n").encode())
        self.assertEqual(result.stderr, b"")

    def check_message(self, ci):
        result = self.run_cli(["auth", "logout", "--output", "json"], ci)
        value = json.loads(result.stdout)
        self.assertIn("Logged out.", json.dumps(value))
        self.assertEqual(result.stdout, (json.dumps(value, indent=2) + "\n").encode())
        self.assertEqual(result.stderr, b"")

    def check_human(self, ci):
        result = self.run_cli(["deployment", "list", "--server", self.address], ci, "160")
        self.assertIn(b"example", result.stdout)
        self.assertIn(b"UNKNOWN", result.stdout)
        self.assertIn(b"Use --output json for full details.", result.stdout)
        self.assertEqual(result.stderr, b"")

    def test_data_ci_true(self):
        self.check_data("true")

    def test_data_ci_false(self):
        self.check_data("false")

    def test_message_ci_true(self):
        self.check_message("true")

    def test_message_ci_false(self):
        self.check_message("false")

    def test_human_ci_true(self):
        self.check_human("true")

    def test_human_ci_false(self):
        self.check_human("false")

    def test_debug_stays_on_stderr(self):
        result = self.run_cli(["auth", "logout", "--output", "json", "--debug"], "true")
        value = json.loads(result.stdout)
        self.assertEqual(result.stdout, (json.dumps(value, indent=2) + "\n").encode())
        self.assertRegex(result.stderr.decode(), r"^\[debug\] fleetctl completed in [\d.]+ ms\n$")


if __name__ == "__main__":
    unittest.main()
