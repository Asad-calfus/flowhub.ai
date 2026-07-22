"""Anonymous workspace scoping - no auth. A workspace is just an opaque string the
client generates and sends back; there is no ownership check beyond that string
matching. `"demo"` (the default when no header is sent) is the pre-existing shared
dataset every prior phase was built against - kept exactly as-is."""

from fastapi import Header

DEMO_WORKSPACE_ID = "demo"


def get_workspace_id(x_workspace_id: str | None = Header(default=None)) -> str:
    return x_workspace_id or DEMO_WORKSPACE_ID
