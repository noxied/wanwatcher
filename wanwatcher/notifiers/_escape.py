"""Escaping helpers for notification bodies.

Untrusted strings reach the notifiers from ipinfo.io (the geo ``org``/``city``/
``region``/``timezone`` fields) and from GitHub release notes. Those must be
neutralised before being placed into HTML email, Telegram ``parse_mode=HTML``
messages, or Discord markdown, otherwise they can inject markup (and, for
Telegram, a stray ``<``/``&`` makes the Bot API reject the message and silently
drop a real alert).
"""

import html as _html
import re
from typing import Any, Optional


def html_escape(value: Optional[Any]) -> str:
    """Escape a value for an HTML context (email). Quote-safe for attributes."""
    return _html.escape("" if value is None else str(value), quote=True)


def telegram_escape(value: Optional[Any]) -> str:
    """Escape a value for Telegram HTML text.

    Telegram's HTML mode treats only ``&``, ``<`` and ``>`` as special in text
    content; escaping just these avoids both injection and the 400 "can't parse
    entities" error that would otherwise drop the message.
    """
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Discord markdown metacharacters that can inject formatting or links from a
# free-text value. Hyphens/hashes are left alone (they only matter at line
# start and would mangle ordinary text like ISP names).
_DISCORD_SPECIAL = re.compile(r"([\\`*_~|\[\]()])")


def discord_escape(value: Optional[Any]) -> str:
    """Backslash-escape Discord markdown metacharacters in a free-text value."""
    text = "" if value is None else str(value)
    return _DISCORD_SPECIAL.sub(r"\\\1", text)
