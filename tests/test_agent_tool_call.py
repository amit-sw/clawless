from clawless.agent import Agent, LLMClient, Message
from clawless.tools.base import Tool, ToolRegistry


class DummyLLM(LLMClient):
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return '{"tool": "echo", "args": {"text": "hi"}}'
        return "final response"


def test_agent_tool_call() -> None:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="echo",
            description="Echo",
            input_schema={"text": "string"},
            handler=lambda args: {"echo": args.get("text")},
        )
    )
    agent = Agent(DummyLLM(), registry)
    response = agent.run("", [Message("user", "hello")])
    assert response == "final response"
