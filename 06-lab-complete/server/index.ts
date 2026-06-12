/**
 * VinWonders AI Scheduler — Production-ready agent server.
 *
 * Productionization (Day 12):
 *   ✅ Config từ environment (12-factor) + fail-fast validate
 *   ✅ Structured JSON logging
 *   ✅ Security headers + CORS từ env
 *   ✅ Rate limiting (per IP) + Cost guard (LLM budget/ngày)
 *   ✅ Optional API key (X-API-Key)
 *   ✅ Health (/health) + Readiness (/ready) probe + /metrics
 *   ✅ Graceful shutdown (SIGTERM/SIGINT)
 *   ✅ Serve built frontend (dist/) → 1 container deploy được cả web + api
 */
import express from 'express'
import cors from 'cors'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { config, validateConfig } from './config'
import { logger } from './logger'
import {
  securityHeaders,
  requestLogger,
  rateLimit,
  requireApiKey,
  costGuardCheck,
  costGuardRecord,
  costGuardStats,
} from './guards'
import { askGemini } from './gemini'
import { ATTRACTIONS, ATTRACTIONS_BY_ID } from '../src/data/attractions'
import { ZONES_BY_ID } from '../src/data/zones'
import type { PlanResponse } from '../src/types'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Fail-fast nếu thiếu config bắt buộc ở production
validateConfig().forEach((w) => logger.warn('config', { message: w }))

const START = Date.now()
let isReady = false

const app = express()
app.set('trust proxy', 1) // sau Nginx/Railway/Render → req.ip lấy từ X-Forwarded-For
app.disable('x-powered-by')
app.use(securityHeaders)
app.use(requestLogger)
app.use(cors({ origin: config.allowedOrigins.includes('*') ? true : config.allowedOrigins }))
app.use(express.json({ limit: '256kb' }))

// Danh sách trò chơi (đưa vào system prompt cho Gemini)
const menu = ATTRACTIONS.map((a) => {
  const timeStr =
    a.showTimes && a.showTimes.length > 0
      ? `giờ diễn: ${a.showTimes.join(', ')}`
      : `mở: ${a.openTime} - đóng: ${a.closeTime}`
  return `${a.id} — ${a.name} — ${ZONES_BY_ID[a.zoneId].name} — ${a.kind} — ${a.durationMin}p — cường độ ${a.intensity} — ${a.kidFriendly ? 'hợp trẻ em' : 'không hợp trẻ nhỏ'} — ${timeStr}`
}).join('\n')

// ── Health / Readiness / Metrics ─────────────────────────────
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    app: config.appName,
    version: config.appVersion,
    environment: config.env,
    uptime_seconds: Math.round((Date.now() - START) / 1000),
    llm: config.geminiApiKey ? 'gemini' : 'unconfigured',
    timestamp: new Date().toISOString(),
  })
})

app.get('/ready', (_req, res) => {
  if (!isReady) return res.status(503).json({ ready: false })
  res.json({ ready: true })
})

app.get('/metrics', (_req, res) => {
  res.json({
    uptime_seconds: Math.round((Date.now() - START) / 1000),
    environment: config.env,
    cost: costGuardStats(),
  })
})

// ── Agent endpoint: POST /api/plan ───────────────────────────
// Bảo vệ: rate limit → (optional) API key → cost guard → Gemini
app.post('/api/plan', rateLimit, requireApiKey, async (req, res) => {
  const { messages = [], itinerarySummary = '', persona = '' } = req.body ?? {}
  try {
    costGuardCheck()

    let out: PlanResponse | null = null
    for (let attempt = 0; attempt < 2 && !out; attempt++) {
      try {
        const r = await askGemini({ messages, itinerarySummary, menu, persona })
        if (r.chosenIds) r.chosenIds = r.chosenIds.filter((id) => ATTRACTIONS_BY_ID[id])
        out = r
      } catch (e) {
        if (attempt === 1) throw e
      }
    }
    costGuardRecord()
    logger.info('agent_response', { action: out?.action, chosen: out?.chosenIds?.length ?? 0 })
    res.json(out)
  } catch (e: any) {
    if (e?.status === 503) return res.status(503).json({ error: e.message })
    logger.error('plan_error', { message: e?.message })
    // Graceful fallback — không lộ stack, trả về clarify để frontend vẫn dùng được
    res.status(200).json({
      action: 'clarify',
      assistantText: 'Xin lỗi, mình gặp trục trặc khi xử lý. Bạn thử nói lại yêu cầu ngắn gọn hơn nhé?',
      clarifyQuestion: 'Bạn muốn chơi từ mấy giờ tới mấy giờ, đoàn có trẻ nhỏ không?',
    } satisfies PlanResponse)
  }
})

// ── Serve built frontend (production single-container) ───────
const distDir = path.resolve(__dirname, '..', 'dist')
if (fs.existsSync(distDir)) {
  app.use(express.static(distDir))
  // SPA fallback — mọi route GET còn lại → index.html (client routing)
  app.get('*', (_req, res) => res.sendFile(path.join(distDir, 'index.html')))
  logger.info('static_enabled', { dir: distDir })
} else {
  logger.warn('static_missing', { message: 'dist/ chưa build — chạy "npm run build" để serve frontend.' })
}

// ── Start + graceful shutdown ────────────────────────────────
const server = app.listen(config.port, () => {
  isReady = true
  logger.info('startup', {
    app: config.appName,
    version: config.appVersion,
    env: config.env,
    port: config.port,
    auth: config.agentApiKey ? 'api-key' : 'public',
  })
})

server.on('error', (err: NodeJS.ErrnoException) => {
  if (err.code === 'EADDRINUSE') {
    logger.error('port_in_use', { port: config.port })
    process.exit(1)
  }
  throw err
})

function shutdown(signal: string) {
  logger.info('shutdown', { signal })
  isReady = false // ngừng nhận traffic mới (readiness fail)
  server.close(() => {
    logger.info('shutdown_complete')
    process.exit(0)
  })
  // Ép thoát nếu quá 10s
  setTimeout(() => process.exit(1), 10_000).unref()
}
process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('SIGINT', () => shutdown('SIGINT'))
