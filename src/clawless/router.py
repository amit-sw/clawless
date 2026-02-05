from __future__ import annotations

import re
from dataclasses import dataclass

TRACK_REGEX = re.compile(r"#track:([A-Za-z0-9_-]{1,32})")


@dataclass
class RoutedMessage:
    text: str
    track_name: str | None


def route_message(text: str) -> RoutedMessage:
    match = TRACK_REGEX.search(text)
    if match:
        cleaned = TRACK_REGEX.sub("", text).strip()
        return RoutedMessage(text=cleaned, track_name=match.group(1))
    return RoutedMessage(text=text, track_name=None)
