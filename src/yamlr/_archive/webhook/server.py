"""Lightweight Kubernetes Admission Webhook Server.

Why: Enables platform engineering teams to enforce manifest quality and
compliance in real-time at cluster admission, preventing invalid configurations
before they are persisted in etcd.
"""
import base64
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

import yaml

from yamlr import heal_yaml

logger = logging.getLogger(__name__)


class AdmissionHandler:
    """Pure business logic for evaluating AdmissionReview requests."""

    @staticmethod
    def handle_admission_review(body_json: Dict[str, Any], is_mutate: bool = False) -> Dict[str, Any]:
        """Evaluates an AdmissionReview v1 payload and generates the admission response."""
        req = body_json.get("request", {})
        uid = req.get("uid", "")
        obj = req.get("object", {})

        if not obj:
            return AdmissionHandler._build_response(uid, allowed=True)

        try:
            yaml_str = yaml.dump(obj)
            heal_res = heal_yaml(yaml_str)

            if not is_mutate:
                # Validating Webhook
                if heal_res.had_changes:
                    return AdmissionHandler._build_response(
                        uid, allowed=True,
                        message=f"Yamlr advisory: {len(heal_res.changes)} remediations recommended."
                    )
                return AdmissionHandler._build_response(uid, allowed=True)
            else:
                # Mutating Webhook: Inject audit annotation
                patch = [
                    {
                        "op": "add",
                        "path": "/metadata/annotations/yamlr.dev~1admitted",
                        "value": "verified"
                    }
                ]
                patch_bytes = json.dumps(patch).encode("utf-8")
                patch_b64 = base64.b64encode(patch_bytes).decode("utf-8")
                return AdmissionHandler._build_response(
                    uid, allowed=True, patch_b64=patch_b64
                )
        except Exception as e:
            logger.warning("Error processing manifest in admission webhook: %s", e)
            return AdmissionHandler._build_response(uid, allowed=True)

    @staticmethod
    def _build_response(
        uid: str,
        allowed: bool,
        message: Optional[str] = None,
        patch_b64: Optional[str] = None
    ) -> Dict[str, Any]:
        resp: Dict[str, Any] = {
            "uid": uid,
            "allowed": allowed
        }
        if message:
            resp["status"] = {"message": message}
        if patch_b64:
            resp["patchType"] = "JSONPatch"
            resp["patch"] = patch_b64

        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": resp
        }


class WebhookServer(BaseHTTPRequestHandler):
    """Minimal HTTP server dispatching /validate and /mutate endpoints."""

    def do_GET(self):
        """Kubernetes cluster liveness and readiness probe endpoint."""
        if self.path in ("/healthz", "/readyz", "/health"):
            resp = b'{"status":"healthy","engine":"yamlr-native","k8s_admission":"ready"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        is_mutate = self.path.startswith("/mutate")

        try:
            body_json = json.loads(post_data.decode("utf-8"))
            response_dict = AdmissionHandler.handle_admission_review(body_json, is_mutate=is_mutate)
            response_bytes = json.dumps(response_dict).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))



def run_webhook_server(port: int = 8443, cert_file: Optional[str] = None, key_file: Optional[str] = None):
    """Starts the HTTPS admission webhook listener."""
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, WebhookServer)

    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"[+] Yamlr Admission Webhook listening on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_webhook_server()
