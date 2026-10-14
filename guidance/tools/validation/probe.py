"""curl-based liveness probing: status parsing, arg building, HEAD/GET probe."""

from __future__ import annotations

import subprocess
from typing import Any

from .const import (
    CURL_STATUS_RE,
    HEAD_FALLBACK_CODES,
    REDIRECT_STATUS_PREFIX,
    SOURCE_RETRIES,
    SOURCE_TIMEOUT,
    SOURCE_USER_AGENT,
    RunnerFn,
)


def parse_curl_status(output: str) -> tuple[str | None, set[str]]:
    """Final ``(status code, redirect locations)`` from curl -i output."""
    code: str | None = None
    locations: set[str] = set()
    for line in output.splitlines():
        line = line.strip()
        match = CURL_STATUS_RE.match(line)
        if match:
            code = match.group(1)
        elif line.lower().startswith("location:"):
            locations.add(line.split(":", 1)[1].strip())
    return code, locations


def curl_args(url: str, head: bool, timeout: float, retries: int) -> list[str]:
    """Polite curl invocation: bounded time, a few retries, named UA."""
    args = [
        "curl", "-sSL",
        "--max-time", str(int(timeout)),
        "--connect-timeout", str(int(timeout)),
        "--retry", str(max(0, int(retries))), "--retry-all-errors",
        "-A", SOURCE_USER_AGENT,
    ]
    if head:
        args.append("-I")
    else:
        args += ["-o", "/dev/null"]
    args.append(url)
    return args


def _run_curl(url: str, head: bool, timeout: float, retries: int, runner: RunnerFn) -> Any | None:
    """Run one curl probe; None when curl itself is missing."""
    try:
        return runner(curl_args(url, head, timeout, retries),
                      capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None


def probe_source(
    url: str,
    timeout: float = SOURCE_TIMEOUT,
    retries: int = SOURCE_RETRIES,
    runner: RunnerFn = subprocess.run,
) -> str:
    """HEAD url (GET fallback on 405/501); return a short status string."""
    proc = _run_curl(url, True, timeout, retries, runner)
    if proc is None:
        return "curl unavailable"
    code, locations = parse_curl_status(proc.stdout)
    if code in HEAD_FALLBACK_CODES:
        proc = _run_curl(url, False, timeout, retries, runner)
        if proc is None:
            return "curl unavailable"
        code, locations = parse_curl_status(proc.stdout)
    if code is None:
        return f"no HTTP status (exit {proc.returncode})"
    if code.startswith(REDIRECT_STATUS_PREFIX) and locations:
        return f"{code} -> {min(locations)}"
    return code
