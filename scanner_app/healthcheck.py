import json
import sys
import urllib.request


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:49173/health"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 1

    if payload.get("ok") is True:
        return 0

    print(f"healthcheck unhealthy: {payload}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
