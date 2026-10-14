"""MUST NOT trigger the LLM tool gate: allowlisted read-only tool with approval."""

ALLOWED_TOOLS = {"read_file": "fs:read"}


def request_approval(tool: str) -> bool:
    return tool in ALLOWED_TOOLS


def agent_step(tool: str, argument: str) -> str:
    if not request_approval(tool):
        raise PermissionError(f"tool {tool} is not allowlisted")
    if tool == "read_file":
        with open(argument, encoding="utf-8") as handle:
            return handle.read()
    raise PermissionError(f"tool {tool} is not allowlisted")
