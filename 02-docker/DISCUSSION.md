# Section 2 — Trả lời câu hỏi thảo luận (Docker)

> Nguồn: [README.md](README.md)

---

## 1. Tại sao `COPY requirements.txt .` rồi `RUN pip install` TRƯỚC khi `COPY . .`?

Vì **Docker layer cache**. Mỗi lệnh trong Dockerfile = 1 layer; layer được cache và chỉ rebuild khi input của nó (hoặc layer phía trước) thay đổi.

- **Code** thay đổi liên tục; **dependencies** thì hiếm khi đổi.
- Nếu `COPY . .` (toàn bộ code) **trước** rồi mới `pip install` → mỗi lần sửa 1 dòng code, cache vô hiệu → **cài lại toàn bộ deps** (chậm, tốn mạng).
- Tách riêng: `COPY requirements.txt` + `pip install` thành layer độc lập → chỉ khi **requirements.txt đổi** mới cài lại. Sửa code chỉ rebuild layer COPY code → **build nhanh hơn rất nhiều**.

→ Đây là tối ưu cache cơ bản nhất của Dockerfile (cả `develop/` lẫn `production/` Dockerfile đều áp dụng).

---

## 2. `.dockerignore` nên chứa những gì? Tại sao `venv/` và `.env` quan trọng?

**Nên chứa:** `__pycache__/`, `*.pyc`, `venv/`/`.venv/`, `.git/`, `.env*` (giữ lại `!.env.example`), IDE files (`.vscode/`, `.idea/`), docs/tests (`*.md`, `tests/`), OS files (`.DS_Store`, `Thumbs.db`).
**Mục tiêu:** build context nhỏ (build nhanh, image gọn) **+ bảo mật**.

- **`venv/`**: là binary cài theo OS/máy host (Linux ≠ Windows ≠ Mac). Copy vào image vừa **vô dụng vừa hỏng** (sai kiến trúc), lại nặng. Phải để `pip install` **trong image** tự tạo môi trường đúng.
- **`.env`**: chứa **secrets**. Copy vào image = **đóng gói secret vào artifact** sẽ bị push/chia sẻ → lộ. Phải loại trừ tuyệt đối; secrets inject qua **env var lúc runtime**. Giữ `.env.example` làm template (không có giá trị thật).

---

## 3. Nếu agent cần đọc file từ disk, làm sao mount volume vào container?

Container là **ephemeral** (xoá là mất dữ liệu) → dùng **volume / bind mount** để data nằm ngoài container.

**Docker CLI:**
```bash
docker run -v /host/path:/app/data agent     # bind mount: file host → container
docker run -v mydata:/app/data agent          # named volume: Docker quản lý
```

**Docker Compose:**
```yaml
services:
  agent:
    volumes:
      - ./data:/app/data         # bind mount (file trên host)
      - agent_data:/app/storage  # named volume (bền, Docker quản lý)
volumes:
  agent_data:
```

**Chọn loại nào:**
- **Bind mount** cho dev — sửa file trên host thấy ngay trong container.
- **Named volume** cho data bền của production (DB, uploads).
- Thêm `:ro` nếu chỉ đọc (như lab mount `nginx.conf:/etc/nginx/nginx.conf:ro`).
- **Lưu ý quyền:** image chạy **non-root user** (production Dockerfile) → cần đảm bảo user đó có quyền ghi vào mount point.
