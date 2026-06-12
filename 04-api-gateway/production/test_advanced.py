"""
Test script cho Full Security Stack (production/app.py).

Chạy server trước:
    python app.py

Rồi chạy test (terminal khác):
    python test_advanced.py                      # chạy tất cả test
    python test_advanced.py --test auth          # chỉ test auth
    python test_advanced.py --test rate-limit    # chỉ test rate limiting
    python test_advanced.py --url http://localhost:8000
"""
import sys
import json
import argparse
import urllib.request
import urllib.error

# Windows console mặc định cp1252 — ép UTF-8 để in tiếng Việt không lỗi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USER = {"username": "student", "password": "demo123"}


def request(url: str, method: str = "GET", token: str | None = None, body: dict | None = None):
    """Gọi API, trả về (status_code, parsed_json_or_None)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or "null")
        except Exception:
            return e.code, None


def login(url: str) -> str:
    status, data = request(f"{url}/auth/token", "POST", body=USER)
    assert status == 200, f"login failed: {status}"
    return data["access_token"]


def test_auth(url: str) -> bool:
    print("== Auth ==")
    s1, _ = request(f"{url}/ask", "POST", body={"question": "hi"})          # no token
    s2, _ = request(f"{url}/auth/token", "POST", body={"username": "student", "password": "x"})
    token = login(url)
    s3, _ = request(f"{url}/ask", "POST", token=token, body={"question": "hi"})
    results = [
        ("no token -> 401", s1 == 401),
        ("bad login -> 401", s2 == 401),
        ("valid token -> 200", s3 == 200),
    ]
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return all(ok for _, ok in results)


def test_rate_limit(url: str) -> bool:
    print("== Rate limit (student = 10 req/min) ==")
    token = login(url)
    codes = []
    for _ in range(13):
        s, _ = request(f"{url}/ask", "POST", token=token, body={"question": "spam"})
        codes.append(s)
    n_ok = codes.count(200)
    n_limited = codes.count(429)
    print(f"  codes: {codes}")
    print(f"  200s={n_ok}  429s={n_limited}")
    ok = n_ok <= 10 and n_limited >= 1
    print(f"  [{'PASS' if ok else 'FAIL'}] vượt quota bị chặn bằng 429")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--test", choices=["auth", "rate-limit", "all"], default="all")
    args = parser.parse_args()

    print(f"Testing security stack @ {args.url}\n")
    results = []
    if args.test in ("auth", "all"):
        results.append(test_auth(args.url))
    if args.test in ("rate-limit", "all"):
        results.append(test_rate_limit(args.url))

    print(f"\n{sum(results)}/{len(results)} test groups passed")
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
