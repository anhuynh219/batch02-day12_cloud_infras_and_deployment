# ============================================================
# VinWonders AI Scheduler — Production Dockerfile (multi-stage)
#   Stage 1: build frontend (Vite → dist/)
#   Stage 2: runtime gọn, non-root, chạy server qua tsx, serve dist/
# Build:  docker build -t vinwonders-agent .
# Run:    docker run -p 8787:8787 -e GEMINI_API_KEY=... vinwonders-agent
# ============================================================

# ── Stage 1: Builder ──────────────────────────────────────
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json .npmrc ./
RUN npm ci
COPY . .
RUN npm run build          # → tạo dist/ (frontend đã bundle)

# ── Stage 2: Runtime ──────────────────────────────────────
FROM node:20-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app

# Chỉ cài dependencies runtime (tsx, express, cors, dotenv, @google/genai...)
COPY package*.json .npmrc ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy frontend đã build + source server/data (server chạy qua tsx)
COPY --from=builder /app/dist ./dist
COPY server ./server
COPY src ./src
COPY public ./public

# Non-root user (security best practice)
RUN useradd -r -u 1001 -m appuser && chown -R appuser /app
USER appuser

ENV PORT=8787
EXPOSE 8787

# Health check — Docker tự restart nếu /health fail (node 20 có global fetch)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://localhost:'+(process.env.PORT||8787)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm", "run", "start"]
