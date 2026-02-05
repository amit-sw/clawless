from __future__ import annotations

import json
import itertools
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class MCPServer:
    name: str
    url: str
    bearer_token: str
    list_method: str = "tools/list"
    call_method: str = "tools/call"


class MCPClient:
    def __init__(self, server: MCPServer, timeout: int = 30):
        self.server = server
        self.timeout = timeout
        self._ids = itertools.count(1)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.server.bearer_token:
            headers["Authorization"] = f"Bearer {self.server.bearer_token}"
        return headers

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": method,
            "params": params or {},
        }
        resp = requests.post(
            self.server.url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._rpc(self.server.list_method)
        tools = result.get("tools") or result.get("result") or []
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._rpc(self.server.call_method, {"name": name, "arguments": arguments})
        return result
