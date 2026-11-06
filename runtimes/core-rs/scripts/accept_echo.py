"""显式执行真实 executable 的关键生命周期验收；无 mock 或测试框架。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    executable = root / "target/debug/examples/echo"
    calls = [
        ("initialize", {}),
        ("start", {"peer_id": "acceptance-peer", "config": {}, "state": {}}),
        ("invoke", {"method": "echo", "params": {"message": "Rust extension acceptance"}}),
        ("stop", None),
    ]
    frames = b"".join(
        json.dumps(
            {"protocol_version": 1, "id": index, "method": method, "params": params}
        ).encode()
        + b"\n"
        for index, (method, params) in enumerate(calls, 1)
    )
    completed = subprocess.run(
        [str(executable)], input=frames, capture_output=True, timeout=15, check=True
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    if len(responses) != 4 or any("error" in response for response in responses):
        raise SystemExit("FAIL: lifecycle response count/error")
    if responses[0]["result"]["name"] != "example/echo":
        raise SystemExit("FAIL: exact extension identity")
    if responses[2]["result"] != {
        "peer_id": "acceptance-peer",
        "echo": {"message": "Rust extension acceptance"},
    }:
        raise SystemExit("FAIL: invocation result")
    if responses[3]["result"] != {"stopped": True}:
        raise SystemExit("FAIL: stop result")
    if [response["id"] for response in responses] != [1, 2, 3, 4]:
        raise SystemExit("FAIL: response identity")
    print("PASS: real executable initialize/start/invoke/stop, protocol-only stdout, clean exit")


if __name__ == "__main__":
    main()
