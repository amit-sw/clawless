from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clawless.mcp.client import MCPClient, MCPServer
from clawless.tools.base import Tool, ToolRegistry


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPToolLoader:
    def __init__(self, client: MCPClient):
        self.client = client

    def list_tool_specs(self) -> list[MCPToolSpec]:
        specs = []
        for tool in self.client.list_tools():
            name = str(tool.get("name", ""))
            if not name:
                continue
            specs.append(
                MCPToolSpec(
                    name=name,
                    description=str(tool.get("description", "")),
                    input_schema=tool.get("inputSchema", tool.get("input_schema", {})) or {},
                )
            )
        return specs

    def register(self, registry: ToolRegistry) -> None:
        for spec in self.list_tool_specs():
            registry.register(
                Tool(
                    name=f"mcp:{self.client.server.name}:{spec.name}",
                    description=spec.description or f"MCP tool {spec.name}",
                    input_schema=spec.input_schema,
                    handler=self._make_handler(spec.name),
                )
            )

    def _make_handler(self, name: str):
        def _handler(args: dict[str, Any]) -> dict[str, Any]:
            return self.client.call_tool(name, args)

        return _handler


def create_loader(server: MCPServer) -> MCPToolLoader:
    return MCPToolLoader(MCPClient(server))
