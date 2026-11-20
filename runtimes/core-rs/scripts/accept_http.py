"""显式运行真实 executable HTTP ingress 的关键验收；不接入自动化测试套件。"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    executable = root / "target/debug/examples/http_echo"
    process = subprocess.Popen(
        [str(executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert process.stdin is not None and process.stdout is not None
    identifier = 0

    def call(method: str, params: object) -> dict:
        nonlocal identifier
        identifier += 1
        process.stdin.write(
            json.dumps(
                {"protocol_version": 1, "id": identifier, "method": method, "params": params}
            ).encode()
            + b"\n"
        )
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        assert response["id"] == identifier and response["protocol_version"] == 1
        return response

    try:
        descriptor = call("initialize", {})["result"]
        ingress = descriptor["capabilities"]["http_ingress"]
        assert ingress["routes"][0]["auth"] == "peer"
        assert ingress["routes"][1]["auth"] == "protocol"
        assert ingress["peer_inbounds"][0]["path"] == "/http-echo/connection"
        assert "error" not in call("start", {"peer_id": "acceptance", "config": {}, "state": {}})
        request = {"method": "PROPFIND", "path": "/http-echo/calendar", "body": ""}
        assert call("http_request", request)["result"]["status"] == 401
        request["headers"] = [{"name": "authorization", "value": list(b"Bearer acceptance")}]
        for invalid_path in ("/http-echox/calendar", "/http-echo/../core", "/http-echo/%63alendar"):
            denied = call("http_request", {**request, "path": invalid_path})
            assert denied["error"]["code"] == "unsupported_capability"
        assert call("http_request", {**request, "method": "DELETE"})["error"]["code"] == (
            "unsupported_capability"
        )
        ordinary = call("invoke", {"method": "x", "params": "x" * (2 * 1024 * 1024)})
        assert ordinary["error"]["code"] == "frame_size"
        body = bytes(range(256)) * (32 * 1024 * 1024 // 256)
        request["body"] = base64.b64encode(body).decode("ascii")
        response = call("http_request", request)["result"]
        decoded = base64.b64decode(response["body"], validate=True)
        assert response["status"] == 200 and len(decoded) == len(body)
        assert hashlib.sha256(decoded).digest() == hashlib.sha256(body).digest()
        assert call("stop", None)["result"]["stopped"]
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    print(
        "PASS: real HTTP ingress descriptor, protocol auth, exact method and path admission, "
        "32 MiB binary round trip, ordinary 1 MiB limit, stop"
    )


if __name__ == "__main__":
    main()
