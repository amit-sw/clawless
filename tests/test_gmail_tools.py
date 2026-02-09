from pathlib import Path
from unittest.mock import MagicMock, patch
import base64

from clawless.tools.base import ToolRegistry
from clawless.tools.gmail_tools import GmailTools


def _make_registry(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    GmailTools(tmp_path).register(registry)
    return registry


def test_gmail_tools_register(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    assert registry.get("gmail_list") is not None
    assert registry.get("gmail_read") is not None
    assert registry.get("gmail_search") is not None


def test_gmail_list_no_credentials(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    tool = registry.get("gmail_list")
    assert tool is not None
    result = tool.handler({})
    assert result["messages"][0]["error"]


def _fake_service(messages_list_return, messages_get_return=None):
    service = MagicMock()
    service.users().messages().list().execute.return_value = messages_list_return
    if messages_get_return:
        service.users().messages().get().execute.return_value = messages_get_return
    return service


def test_gmail_list_with_mock(tmp_path: Path) -> None:
    tools = GmailTools(tmp_path)
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {"messages": []}
    with patch.object(tools, "_get_service", return_value=mock_service):
        result = tools.gmail_list({"max_results": 5})
    assert result["count"] == 0
    assert result["messages"] == []


def test_gmail_read_missing_id(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    tool = registry.get("gmail_read")
    assert tool is not None
    result = tool.handler({})
    assert result["error"] == "message_id is required"


def test_gmail_search_missing_query(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    tool = registry.get("gmail_search")
    assert tool is not None
    result = tool.handler({})
    assert result["error"] == "query is required"


def test_gmail_read_with_mock(tmp_path: Path) -> None:
    tools = GmailTools(tmp_path)
    body_data = base64.urlsafe_b64encode(b"Hello, world!").decode()
    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = {
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
            ],
            "body": {"data": body_data},
        }
    }
    with patch.object(tools, "_get_service", return_value=mock_service):
        result = tools.gmail_read({"message_id": "abc123"})
    assert result["subject"] == "Test Email"
    assert result["from"] == "alice@example.com"
    assert result["body"] == "Hello, world!"


def test_extract_body_html(tmp_path: Path) -> None:
    tools = GmailTools(tmp_path)
    html_data = base64.urlsafe_b64encode(b"<p>Hello &amp; welcome</p>").decode()
    payload = {
        "mimeType": "text/html",
        "body": {"data": html_data},
    }
    body = tools._extract_body(payload)
    assert "Hello" in body
    assert "welcome" in body
    assert "<p>" not in body
