"""Execute every algorithm in its own E2B Sandbox; no API key is uploaded."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from .evaluator import sha256_string


@dataclass
class RawCandidate:
    name: str
    seed: int
    source_sha256: str
    sandbox_id: str = ""
    elapsed_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    output: Any = None
    output_sha256: str | None = None
    error: str | None = None


def _run_one(sandbox, *, name: str, seed: int, code_hash: str, timeout: int) -> RawCandidate:
    raw = RawCandidate(name=name, seed=seed, source_sha256=code_hash,
                       sandbox_id=sandbox.sandbox_id)
    began = time.monotonic()
    try:
        # Remove old output so no previous seed can be accidentally scored.
        result = sandbox.commands.run(
            "rm -f /home/user/output.json && python /home/user/solver.py", timeout=timeout
        )
        raw.stdout = (result.stdout or "")[-3000:]
        raw.stderr = (result.stderr or "")[-3000:]
        if result.exit_code != 0:
            raw.error = f"実行終了コード: {result.exit_code}"
        else:
            text = sandbox.files.read("/home/user/output.json")
            if not isinstance(text, str):
                raise ValueError("出力をテキストとして読み取れませんでした。")
            if len(text) > 200_000:
                raise ValueError("出力JSONが200KBの上限を超えました。")
            raw.output_sha256 = sha256_string(text)
            raw.output = json.loads(text)
    except Exception as exc:
        raw.stderr = (str(getattr(exc, "stderr", "")) or raw.stderr)[-3000:]
        raw.stdout = (str(getattr(exc, "stdout", "")) or raw.stdout)[-3000:]
        raw.error = f"{type(exc).__name__}: {str(exc)[:300]}"
    finally:
        raw.elapsed_seconds = round(time.monotonic() - began, 3)
    return raw


def run_in_e2b(datasets: dict[int, dict], sources: dict[str, str]) -> dict[str, list[RawCandidate]]:
    """Each approach has a separate sandbox; every seed uses the same input.

    Runs are sequential to cap sandbox consumption. A failed command is kept as
    evidence. Sandbox initialization errors propagate; no fake results.
    """
    key = os.getenv("E2B_API_KEY", "").strip()
    if not key:
        raise RuntimeError("E2B_API_KEY が未設定です。")
    from e2b import Sandbox
    timeout = int(os.getenv("E2B_SANDBOX_TIMEOUT_SECONDS", "180"))
    command_timeout = int(os.getenv("E2B_COMMAND_TIMEOUT_SECONDS", "45"))
    evidence = {}
    for name, code in sources.items():
        with Sandbox.create(api_key=key, timeout=timeout,
                            allow_internet_access=False) as sandbox:
            sandbox.files.write("/home/user/solver.py", code)
            source_hash = sha256_string(code)
            series = []
            for seed, data in datasets.items():
                sandbox.files.write("/home/user/input.json", json.dumps(data, ensure_ascii=False))
                series.append(_run_one(sandbox, name=name, seed=seed,
                                       code_hash=source_hash, timeout=command_timeout))
            evidence[name] = series
    return evidence
