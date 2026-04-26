import json
import time
import urllib.request
from pathlib import Path

from .config import ASR_SERVER_URL, MODEL_NAME


def load_model():
    if ASR_SERVER_URL:
        return None

    from parakeet_mlx import from_pretrained

    return from_pretrained(MODEL_NAME)


def extract_text(result) -> str:
    if hasattr(result, "sentences") and result.sentences:
        lines = []

        for sentence in result.sentences:
            sentence_text = getattr(sentence, "text", "").strip()

            if sentence_text:
                lines.append(sentence_text)

        if lines:
            return "\n".join(lines)

    if hasattr(result, "text"):
        return result.text

    return str(result)


def transcribe_segment(segment_path: Path, model, feed_name: str) -> str:
    if ASR_SERVER_URL:
        return transcribe_via_server(segment_path, feed_name)

    return extract_text(model.transcribe(str(segment_path)))


def transcribe_via_server(segment_path: Path, feed_name: str) -> str:
    payload = json.dumps(
        {
            "feed_name": feed_name,
            "segment_path": str(segment_path),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{ASR_SERVER_URL}/transcribe",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = time.time()

    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "error" in data:
        raise RuntimeError(data["error"])

    if "duration_ms" not in data:
        data["duration_ms"] = int((time.time() - started_at) * 1000)

    return str(data.get("text", ""))
