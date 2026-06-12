# Section 4 — Trả lời câu hỏi thảo luận (API Gateway & Security)

> Nguồn: [README.md](README.md)

---

## 1. Khi nào nên dùng API Key vs JWT vs OAuth2?

| | API Key | JWT | OAuth2 / OIDC |
|---|---------|-----|---------------|
| Định danh | **App/client** (không phải user) | **User** (có claims: id, role) | User, qua bên thứ 3 |
| State | Static, lâu dài | Stateless, có expiry | Delegated, có scope |
| Hợp với | Internal API, B2B, server-to-server, MVP | App có user/role, session ngắn | "Login with Google/GitHub", uỷ quyền |
| Độ phức tạp | Thấp | Trung bình | Cao (thường dùng provider) |
| Trong lab | `develop/` (X-API-Key) | `production/` (auth.py) | — |

- **API Key**: đơn giản nhất, nhưng không tự hết hạn, lộ là toang, không phân biệt user/scope mịn.
- **JWT**: tự ký + verify, chứa role → không cần query DB mỗi request. Nhược: khó revoke trước hạn (cần blacklist), payload chỉ **signed** chứ không encrypted (đừng để secret trong payload).
- **OAuth2/OIDC**: cho consumer-facing, delegated access, scope hẹp. Phức tạp nhất; thường dùng Auth0/Clerk/Cognito.

**Quy tắc chọn:** máy-với-máy/đơn giản → **API Key**; có user + role, tự quản → **JWT**; đăng nhập bên thứ 3/uỷ quyền → **OAuth2**. Có thể kết hợp: OAuth2 để login → phát JWT để gọi API → API Key cho integration B2B.

---

## 2. Rate limit nên đặt bao nhiêu request/phút cho một AI agent?

Không có con số vàng — phụ thuộc **chi phí mỗi call** (LLM đắt + chậm hơn API CRUD rất nhiều), **tier user**, và mục tiêu chống abuse.

- **Tham chiếu lab** (`rate_limiter.py`): user **10/min**, admin **100/min**. Nhỏ vì mỗi call LLM tốn tiền + latency cao — khác hẳn API thường có thể 1000/min.
- **Cách đặt**: bắt đầu thấp & an toàn rồi nới dần; phân tier (free thấp, paid cao); lưu ý 1 "request" của agent có thể fan-out nhiều LLM call nội bộ.
- **Nhiều tầng** mới đủ: per-minute (chống burst) **+** daily quota **+** cost guard (chống bill sốc). Trả `429` kèm `Retry-After` và header `X-RateLimit-*`.

**Rule of thumb:** free user vài–10 req/phút ("đủ cho người thật dùng thoải mái, đủ chặn script spam"). **Ghép với cost guard quan trọng hơn con số chính xác** — vì kẻ tấn công đốt tiền nhanh hơn đốt request.

---

## 3. Nếu API key bị lộ, phát hiện và xử lý như thế nào?

**Phát hiện:**
- Theo dõi bất thường: spike request, IP/địa lý lạ, vượt budget đột ngột (cost guard giúp), 1 key liên tục chạm rate limit/budget.
- Quét secret trong git: GitHub secret scanning, `gitleaks`, pre-commit hook.
- Log + alert (không log chính cái key — `production/app.py` đã tránh log secret).

**Xử lý (incident response):**
1. **Revoke/rotate ngay** key bị lộ → vô hiệu hoá. (Vì sao thiết kế nên hỗ trợ nhiều key + revoke.)
2. Phát key mới cho client hợp lệ, cập nhật secret store.
3. Điều tra log: key bị dùng làm gì, thiệt hại (tiền, data).
4. Nếu đã commit lên git: xoá khỏi **history** (BFG/git-filter-repo) và **coi như đã lộ vĩnh viễn** (đã bị clone/cache/index).
5. Hậu kiểm: thêm scanning, expiry/rotation định kỳ, scope least-privilege, dùng Secret Manager.

**Phòng ngừa:** key có thời hạn + rotation, scope hẹp, lưu ở Secret Manager (không hardcode — đúng bài 01 & 03), không bao giờ log secret.
