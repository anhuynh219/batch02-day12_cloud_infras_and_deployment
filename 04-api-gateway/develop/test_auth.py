"""
Test script cho API Key Authentication (develop/app.py).

Chạy server trước:
    AGENT_API_KEY=my-secret-key python app.py

Rồi chạy test (terminal khác):
    AGENT_API_KEY=my-secret-key python test_auth.py
    python test_auth.py --url http://localhost:8000 --key my-secret-key
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error

# Windows console mặc định cp1252 — ép UTF-8 để in tiếng Việt không lỗi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def call(url: str, key: str | None) -> int:
    """POST /ask?question=hello, trả về HTTP status code."""
    req = urllib.request.Request(
        f"{url}/ask?question=hello",
        method="POST",
        headers={"X-API-Key": key} if key else {},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--key", default=os.getenv("AGENT_API_KEY", "demo-key-change-in-production"))
    args = parser.parse_args()

    cases = [
        ("Không có key",   None,          401),
        ("Sai key",        "wrong-key",   403),
        ("Đúng key",       args.key,      200),
    ]

    print(f"Testing API Key auth @ {args.url}\n")
    passed = 0
    for name, key, expected in cases:
        got = call(args.url, key)
        ok = got == expected
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<14} expected={expected} got={got}")

    print(f"\n{passed}/{len(cases)} passed")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
