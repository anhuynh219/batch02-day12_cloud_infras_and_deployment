"""
auto_demo.py — TỰ ĐỘNG demo Section 5 (Scaling & Reliability).

Script này tự làm hết, KHÔNG cần thao tác tay:
  1. Khởi động 2 instance của stateless agent (in-memory, không Redis) trên cổng 8101/8102
  2. Kiểm tra health/readiness
  3. Chat trên 1 instance  → session liền mạch ✅
  4. Chat luân phiên 2 instance → session bị đứt ⚠️ (vì không chia sẻ store)
  5. In kết luận, rồi TỰ TẮT 2 instance (dọn sạch)

Chạy (từ thư mục 05-scaling-reliability):
    uv run --with fastapi --with "uvicorn[standard]" --with pydantic python auto_demo.py
"""
import os
import sys
import time
import json
import subprocess
import tempfile
import urllib.request
import urllib.error

# Windows console cp1252 → ép UTF-8 để in tiếng Việt/emoji không lỗi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.join(HERE, "production")
INSTANCES = [("instance-A", 8101), ("instance-B", 8102)]


def line(c="─"):
    print(c * 64)


def title(t):
    print()
    line("=")
    print("  " + t)
    line("=")


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or "null")
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, {"error": str(e)}


def start_instance(instance_id, port, logfile):
    env = dict(os.environ)
    env["INSTANCE_ID"] = instance_id
    env["PYTHONIOENCODING"] = "utf-8"
    env["PORT"] = str(port)
    # Chạy uvicorn trực tiếp (không --reload) → 1 process, dễ tắt, không zombie
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=PROD, env=env, stdout=logfile, stderr=subprocess.STDOUT,
    )


def wait_health(port, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        status, _ = http("GET", f"http://127.0.0.1:{port}/health")
        if status == 200:
            return True
        time.sleep(0.4)
    return False


def main():
    procs, logs = [], []
    title("DEMO SECTION 5 — SCALING & RELIABILITY (chạy tự động)")
    print("Khởi động 2 instance stateless agent (in-memory, KHÔNG Redis)...")

    for inst, port in INSTANCES:
        lf = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{inst}.log", mode="w", encoding="utf-8")
        logs.append(lf.name)
        procs.append(start_instance(inst, port, lf))

    try:
        for (inst, port), logname in zip(INSTANCES, logs):
            if not wait_health(port):
                print(f"❌ {inst} (cổng {port}) không khởi động được. Log:")
                print(open(logname, encoding="utf-8", errors="replace").read()[-1200:])
                return
            print(f"  ✅ {inst} sẵn sàng tại http://127.0.0.1:{port}")

        # ── 1) HEALTH vs READINESS ───────────────────────────────
        title("1) HEALTH (liveness) vs READINESS — 'máy còn sống & sẵn sàng?'")
        for inst, port in INSTANCES:
            sh, dh = http("GET", f"http://127.0.0.1:{port}/health")
            sr, _ = http("GET", f"http://127.0.0.1:{port}/ready")
            print(f"  {inst}:  /health → HTTP {sh} ({dh.get('status')}, storage={dh.get('storage')})   /ready → HTTP {sr}")
        print()
        print("  → /health FAIL: platform RESTART máy.  /ready FAIL: chỉ NGỪNG đẩy traffic (không restart).")

        # ── 2) 1 INSTANCE: session OK ────────────────────────────
        title("2) CHAT TRÊN 1 INSTANCE — session liền mạch ✅")
        a_port = INSTANCES[0][1]
        questions = ["What is Docker?", "And Kubernetes?", "Why containers?"]
        sid = None
        for i, q in enumerate(questions, 1):
            _, d = http("POST", f"http://127.0.0.1:{a_port}/chat", {"question": q, "session_id": sid})
            sid = d["session_id"]
            print(f"  Lượt {i}:  Q='{q}'")
            print(f"           → served_by={d['served_by']}  turn={d['turn']}  storage={d['storage']}")
        _, h = http("GET", f"http://127.0.0.1:{a_port}/chat/{sid}/history")
        print(f"\n  History trên instance-A: {h['count']} messages  ({len(questions)} hỏi + {len(questions)} đáp)")
        print("  → Chỉ 1 instance phục vụ → nhớ HẾT → hội thoại liền mạch.")

        # ── 3) NHIỀU INSTANCE + IN-MEMORY: session breaks ────────
        title("3) NHIỀU INSTANCE + IN-MEMORY — session bị ĐỨT ⚠️")
        print("  Giả lập load balancer: CÙNG 1 session, gửi LUÂN PHIÊN A → B → A → B\n")
        sid = None
        convo = ["What is Docker?", "And Kubernetes?", "Tell me more", "What did I ask first?"]
        for i, q in enumerate(convo):
            inst, port = INSTANCES[i % 2]
            _, d = http("POST", f"http://127.0.0.1:{port}/chat", {"question": q, "session_id": sid})
            sid = d["session_id"]
            print(f"  Lượt {i + 1} → {inst}:  turn={d['turn']}   Q='{q}'")
        _, ha = http("GET", f"http://127.0.0.1:{INSTANCES[0][1]}/chat/{sid}/history")
        _, hb = http("GET", f"http://127.0.0.1:{INSTANCES[1][1]}/chat/{sid}/history")
        print()
        print(f"  History trên instance-A: {ha['count']} messages")
        print(f"  History trên instance-B: {hb['count']} messages")
        print(f"  → {len(convo)} lượt cùng 1 session bị XÉ ĐÔI: mỗi máy chỉ nhớ phần mình nhận.")
        print("    'turn' không tăng đều, không máy nào đủ ngữ cảnh → chatbot 'QUÊN' user vừa nói gì.")

        # ── 4) KẾT LUẬN ──────────────────────────────────────────
        title("4) KẾT LUẬN")
        print("  • 1 instance        → in-memory đủ, session ổn.")
        print("  • Nhiều instance    → in-memory VỠ session (vừa thấy ở phần 3).")
        print("  • Lời giải          → STATELESS + REDIS chung: mọi instance đọc cùng 1 store.")
        print("                        docker compose -f production/docker-compose.yml up --scale agent=3")
        print("                        (khi đó storage='redis', history liền mạch dù served_by đổi.)")
        print()

    finally:
        print("Đang tắt 2 instance demo...")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        for n in logs:
            try:
                os.unlink(n)
            except Exception:
                pass
        print("✅ Xong — đã dọn sạch, không còn server nào chạy ngầm.")


if __name__ == "__main__":
    main()
