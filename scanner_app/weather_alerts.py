import os
import re
import sys
from dataclasses import dataclass


USE_COLOR = os.getenv("NO_COLOR") is None and sys.stdout.isatty()
USE_EMOJI = os.getenv("NO_EMOJI") is None

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"
RED = "\033[31m"
WHITE_ON_RED = "\033[97;41m"


@dataclass(frozen=True)
class WeatherAlert:
    severity: int
    label: str
    emoji: str
    color: str
    matched: str


WEATHER_RULES: list[tuple[int, str, str, str, list[str]]] = [
    (
        4,
        "WX-4",
        "🚨",
        WHITE_ON_RED,
        [
            r"\btornado emergency\b",
            r"\btake shelter\b",
            r"\blarge and destructive tornado\b",
            r"\bdebris signature\b",
            r"\bcatastrophic\b",
            r"\bpds tornado warning\b",
            r"\bparticularly dangerous situation\b",
        ],
    ),
    (
        3,
        "WX-3",
        "🔴",
        RED,
        [
            r"\btornado warning\b",
            r"\bconfirmed tornado\b",
            r"\btornado on the ground\b",
            r"\btornado observed\b",
            r"\bradar indicated tornado\b",
            r"\bobserved tornado\b",
        ],
    ),
    (
        2,
        "WX-2",
        "🟠",
        ORANGE,
        [
            r"\btornado watch\b",
            r"\bfunnel cloud\b",
            r"\bwall cloud\b",
            r"\brotating wall cloud\b",
            r"\bradar indicated rotation\b",
            r"\bspotter reported rotation\b",
            r"\bsevere thunderstorm warning\b",
        ],
    ),
    (
        1,
        "WX-1",
        "🟡",
        YELLOW,
        [
            r"\brotation\b",
            r"\bstrong rotation\b",
            r"\bbroad rotation\b",
            r"\blowering\b",
            r"\bhail\b",
            r"\blarge hail\b",
            r"\bstrong winds?\b",
            r"\bstorm damage\b",
            r"\bheavy rain\b",
            r"\bflash flooding\b",
        ],
    ),
]


def detect_weather_alert(text: str) -> WeatherAlert | None:
    normalized = re.sub(r"\s+", " ", text).strip().lower()

    for severity, label, emoji, color, patterns in WEATHER_RULES:
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)

            if match:
                return WeatherAlert(
                    severity=severity,
                    label=label,
                    emoji=emoji,
                    color=color,
                    matched=match.group(0),
                )

    return None


def colorize_weather_terms(text: str, alert: WeatherAlert | None) -> str:
    if not alert or not USE_COLOR:
        return text

    color = alert.color

    for _severity, _label, _emoji, _color, patterns in WEATHER_RULES:
        for pattern in patterns:
            text = re.sub(
                pattern,
                lambda match: f"{BOLD}{color}{match.group(0).upper()}{RESET}{color}",
                text,
                flags=re.IGNORECASE,
            )

    return text


def format_terminal_block(
    timestamp: str,
    feed_name: str,
    text: str,
    alert: WeatherAlert | None = None,
) -> str:
    if alert is None:
        alert = detect_weather_alert(text)

    if not alert:
        return f"[{timestamp}] [{feed_name}]\n{text}\n\n"

    emoji = f"{alert.emoji} " if USE_EMOJI else ""
    prefix = f"{emoji}{alert.label}"
    highlighted_text = colorize_weather_terms(text, alert)

    if not USE_COLOR:
        return f"{prefix} [{timestamp}] [{feed_name}]\n{highlighted_text}\n\n"

    return (
        f"{alert.color}{BOLD}{prefix}{RESET} "
        f"{DIM}[{timestamp}] [{feed_name}]{RESET}\n"
        f"{alert.color}{highlighted_text}{RESET}\n\n"
    )
