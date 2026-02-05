from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from clawless.tools.base import ToolRegistry

TOOL_CALL_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Message:
    role: str
    content: str


class LLMClient:
    def invoke(self, messages: list[Message]) -> str:
        raise NotImplementedError


class LangChainLLMClient(LLMClient):
    def __init__(self, connection_string: str, api_key: str) -> None:
        self.connection_string = connection_string
        self.api_key = api_key
        self.model = self._init_model()

    def _init_model(self):
        if ":" not in self.connection_string:
            raise ValueError("connection_string must be scheme:model")
        scheme, model_name = self.connection_string.split(":", 1)
        scheme = scheme.lower()
        if scheme in {"openai", "openrouter"}:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:  # noqa: BLE001
                raise RuntimeError("langchain-openai is required for OpenAI/OpenRouter") from exc
            base_url = None
            if scheme == "openrouter":
                base_url = "https://openrouter.ai/api/v1"
            return ChatOpenAI(model=model_name, api_key=self.api_key, base_url=base_url)
        raise ValueError(f"Unsupported LLM scheme: {scheme}")

    def invoke(self, messages: list[Message]) -> str:
        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("langchain-core is required for message handling") from exc
        formatted = []
        for msg in messages:
            if msg.role == "system":
                formatted.append(SystemMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted.append(AIMessage(content=msg.content))
            else:
                formatted.append(HumanMessage(content=msg.content))
        response = self.model.invoke(formatted)
        return getattr(response, "content", str(response))


class Agent:
    def __init__(self, llm: LLMClient, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools

    def run(self, track_summary: str, messages: list[Message]) -> str:
        system_prompt = self._build_system_prompt(track_summary)
        tool_prompt = self._build_tool_prompt()
        request = [Message("system", system_prompt), Message("system", tool_prompt)] + messages
        response = self.llm.invoke(request)
        tool_call = self._parse_tool_call(response)
        if not tool_call:
            return response
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Tool not found: {tool_name}"
        result = tool.handler(args)
        followup = request + [
            Message("assistant", response),
            Message("system", f"Tool result: {json.dumps(result)}"),
        ]
        final_response = self.llm.invoke(followup)
        return final_response

    def _build_system_prompt(self, summary: str) -> str:
        parts = [
            "You are a helpful assistant.",
            "You have access to tools when necessary.",
        ]
        if summary:
            parts.append(f"Track summary: {summary}")
        return "\n".join(parts)

    def _build_tool_prompt(self) -> str:
        tool_lines = []
        for tool in self.tools.list_tools():
            tool_lines.append(f"- {tool.name}: {tool.description}")
        tool_desc = "\n".join(tool_lines) if tool_lines else "(no tools)"
        return (
            "If you need to use a tool, respond with a single JSON object on its own line, "
            "formatted as {\"tool\": \"tool_name\", \"args\": { ... }}. "
            "Otherwise respond normally.\n"
            f"Available tools:\n{tool_desc}"
        )

    @staticmethod
    def _parse_tool_call(response: str) -> dict[str, Any] | None:
        text = response.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
        else:
            data = None
        if data is None:
            match = TOOL_CALL_PATTERN.search(response)
            if not match:
                return None
            snippet = match.group(0)
            try:
                data = json.loads(snippet)
            except json.JSONDecodeError:
                return None
        if not isinstance(data, dict) or "tool" not in data:
            return None
        return data
