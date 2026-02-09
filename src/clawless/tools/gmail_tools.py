from __future__ import annotations

import base64
import html
import re
from pathlib import Path
from typing import Any

from clawless.tools.base import Tool, ToolRegistry

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILENAME = "gmail_token.json"
CREDENTIALS_FILENAME = "gmail_credentials.json"


class GmailTools:
    def __init__(self, config_root: Path):
        self.config_root = Path(config_root)

    def register(self, registry: ToolRegistry) -> None:
        registry.register(
            Tool(
                name="gmail_list",
                description=(
                    "Fetch ALL emails from a time period with full content and reply status. "
                    "Returns subject, sender, date, body, and whether you already replied. "
                    "No cap on results — returns every email in the period. "
                    "Use the 'days' arg to control how far back (default 1 day)."
                ),
                input_schema={
                    "query": "optional Gmail search query to filter results",
                    "days": "how many days back to look (default 1)",
                },
                handler=self.gmail_list,
            )
        )
        registry.register(
            Tool(
                name="gmail_read",
                description="Read the full content of a specific email by its message ID.",
                input_schema={"message_id": "the Gmail message ID"},
                handler=self.gmail_read,
            )
        )
        registry.register(
            Tool(
                name="gmail_search",
                description=(
                    "Search emails using Gmail query syntax with full content and reply status. "
                    "Examples: from:boss, subject:invoice, has:attachment, newer_than:3d"
                ),
                input_schema={
                    "query": "Gmail search query (required)",
                    "max_results": "number of emails to return (default 20)",
                },
                handler=self.gmail_search,
            )
        )

    def _get_service(self) -> Any:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        token_path = self.config_root / TOKEN_FILENAME
        creds_path = self.config_root / CREDENTIALS_FILENAME

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=creds)

    def _extract_headers(self, headers: list[dict]) -> dict[str, str]:
        result: dict[str, str] = {}
        for h in headers:
            name = h.get("name", "").lower()
            if name in ("from", "to", "subject", "date"):
                result[name] = h.get("value", "")
        return result

    def _extract_body(self, payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        if mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", raw)
                return html.unescape(text).strip()
        for part in payload.get("parts", []):
            body = self._extract_body(part)
            if body:
                return body
        return ""

    def _get_user_email(self, service: Any) -> str:
        """Get the authenticated user's email address."""
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")

    def _check_replied(self, service: Any, thread_id: str, user_email: str) -> bool:
        """Check if the user has sent a reply in this thread."""
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From"],
        ).execute()
        messages = thread.get("messages", [])
        if len(messages) <= 1:
            return False
        for msg in messages[1:]:
            headers = msg.get("payload", {}).get("headers", [])
            for h in headers:
                if h.get("name", "").lower() == "from":
                    if user_email.lower() in h.get("value", "").lower():
                        return True
        return False

    def _fetch_all_message_ids(self, service: Any, query: str) -> list[dict]:
        """Fetch all message IDs matching the query, paginating through all results."""
        all_messages: list[dict] = []
        page_token = None
        while True:
            kwargs: dict[str, Any] = {"userId": "me", "q": query, "maxResults": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            resp = service.users().messages().list(**kwargs).execute()
            all_messages.extend(resp.get("messages", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return all_messages

    def _fetch_full_messages(self, service: Any, query: str, max_results: int = 0) -> list[dict[str, Any]]:
        """Fetch messages with full content and reply status.

        Args:
            service: Gmail API service
            query: Gmail search query
            max_results: Max messages to fetch. 0 means no limit (fetch all).
        """
        if service is None:
            return [{"error": "Gmail credentials not found. Place gmail_credentials.json in ~/.clawless/"}]

        if max_results > 0:
            # Use a single API call with maxResults
            resp = service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            message_ids = resp.get("messages", [])
        else:
            # Fetch ALL matching messages
            message_ids = self._fetch_all_message_ids(service, query)

        if not message_ids:
            return []

        user_email = self._get_user_email(service)

        # Batch fetch full content for all messages
        fetched: dict[str, dict] = {}

        def _callback(request_id: str, response: dict, exception: Any) -> None:
            if exception is None:
                fetched[request_id] = response

        # Gmail batch API allows max 100 per batch
        for i in range(0, len(message_ids), 100):
            batch = service.new_batch_http_request(callback=_callback)
            for msg_ref in message_ids[i:i + 100]:
                batch.add(
                    service.users().messages().get(
                        userId="me", id=msg_ref["id"], format="full",
                    ),
                    request_id=msg_ref["id"],
                )
            batch.execute()

        results = []
        # Collect thread IDs for reply checking
        thread_ids: dict[str, list[str]] = {}
        for msg_ref in message_ids:
            msg = fetched.get(msg_ref["id"])
            if not msg:
                continue
            tid = msg.get("threadId", "")
            if tid not in thread_ids:
                thread_ids[tid] = []
            thread_ids[tid].append(msg_ref["id"])

        # Batch check reply status for all threads
        thread_replied: dict[str, bool] = {}
        for tid in thread_ids:
            thread_replied[tid] = self._check_replied(service, tid, user_email)

        for msg_ref in message_ids:
            msg = fetched.get(msg_ref["id"])
            if not msg:
                continue
            headers = self._extract_headers(msg.get("payload", {}).get("headers", []))
            body = self._extract_body(msg.get("payload", {}))
            labels = msg.get("labelIds", [])
            tid = msg.get("threadId", "")
            results.append({
                "message_id": msg_ref["id"],
                "thread_id": tid,
                "subject": headers.get("subject", "(no subject)"),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "body": body[:5000],
                "replied": thread_replied.get(tid, False),
                "is_unread": "UNREAD" in labels,
            })
        return results

    def gmail_list(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        days = int(args.get("days", 1))
        full_query = f"newer_than:{days}d {query}".strip()
        service = self._get_service()
        messages = self._fetch_full_messages(service, full_query, max_results=0)
        return {"query": full_query, "count": len(messages), "messages": messages}

    def gmail_read(self, args: dict[str, Any]) -> dict[str, Any]:
        message_id = str(args.get("message_id", ""))
        if not message_id:
            return {"error": "message_id is required"}

        service = self._get_service()
        if service is None:
            return {"error": "Gmail credentials not found. Place gmail_credentials.json in ~/.clawless/"}

        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        headers = self._extract_headers(msg.get("payload", {}).get("headers", []))
        body = self._extract_body(msg.get("payload", {}))
        return {
            "message_id": message_id,
            "subject": headers.get("subject", "(no subject)"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "date": headers.get("date", ""),
            "body": body[:10000],
        }

    def gmail_search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        if not query:
            return {"error": "query is required"}
        max_results = int(args.get("max_results", 20))
        service = self._get_service()
        messages = self._fetch_full_messages(service, query, max_results=max_results)
        return {"query": query, "count": len(messages), "messages": messages}
