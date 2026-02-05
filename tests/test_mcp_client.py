import json

import requests

from clawless.mcp.client import MCPClient, MCPServer


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_mcp_client_list_and_call(monkeypatch):
    def fake_post(url, headers=None, data=None, timeout=None):
        request = json.loads(data)
        method = request.get("method")
        if method == "tools/list":
            result = {"tools": [{"name": "ping", "description": "Ping"}]}
        elif method == "tools/call":
            params = request.get("params", {})
            result = {"echo": params}
        else:
            result = {"error": "unknown method"}
        payload = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
        return FakeResponse(payload)

    monkeypatch.setattr(requests, "post", fake_post)

    client = MCPClient(MCPServer(name="local", url="http://example.com", bearer_token=""))
    tools = client.list_tools()
    assert tools[0]["name"] == "ping"

    result = client.call_tool("ping", {"value": 1})
    assert result["echo"]["name"] == "ping"
