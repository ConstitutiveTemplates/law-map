"""MUST trigger the LLM tool gate: unbounded shell tool with no approval hook."""

import subprocess

TOOLS = {"shell": subprocess.run}


def agent_step(command: str) -> str:
    return TOOLS["shell"](command, shell=True, capture_output=True, text=True).stdout
