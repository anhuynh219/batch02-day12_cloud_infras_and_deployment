/**
 * Lớp bảo vệ trước agent: security headers, request logging, rate limit,
 * optional API key, cost guard (budget số lần gọi LLM / ngày).
 *
 * Luồng: Security headers → Logging → Rate limit (429) → API key (401) → Cost guard (503) → Agent
 */
import type { Request, Response, NextFunction } from 'express'
import { config } from './config'
import { logger } from './logger'

// ── Security headers ─────────────────────────────────────────
export function securityHeaders(_req: Request, res: Response, next: NextFunction) {
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('X-Frame-Options', 'DENY')
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin')
  res.removeHeader('X-Powered-By')
  next()
}

// ── Request logging (structured) ─────────────────────────────
export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const start = Date.now()
  res.on('finish', () => {
    logger.info('request', {
      method: req.method,
      path: req.path,
      status: res.statusCode,
      ms: Date.now() - start,
    })
  })
  next()
}

// ── Rate limiter (in-memory sliding window per IP) ───────────
// Production thật: thay bằng Redis để chia sẻ giữa các instance.
const windows = new Map<string, number[]>()
export function rateLimit(req: Request, res: Response, next: NextFunction) {
  const key = req.ip || 'unknown'
  const now = Date.now()
  const recent = (windows.get(key) ?? []).filter((t) => t > now - 60_000)
  if (recent.length >= config.rateLimitPerMinute) {
    res.setHeader('Retry-After', '60')
    res.setHeader('X-RateLimit-Limit', String(config.rateLimitPerMinute))
    res.setHeader('X-RateLimit-Remaining', '0')
    return res.status(429).json({
      error: 'Rate limit exceeded',
      limit: config.rateLimitPerMinute,
      window_seconds: 60,
    })
  }
  recent.push(now)
  windows.set(key, recent)
  next()
}

// ── Optional API key (chỉ bật khi AGENT_API_KEY được đặt) ────
export function requireApiKey(req: Request, res: Response, next: NextFunction) {
  if (!config.agentApiKey) return next()
  if (req.header('X-API-Key') !== config.agentApiKey) {
    return res.status(401).json({ error: 'Invalid or missing API key. Header: X-API-Key: <key>' })
  }
  next()
}

// ── Cost guard (budget số lần gọi LLM / ngày) ────────────────
let day = new Date().toISOString().slice(0, 10)
let calls = 0
export function costGuardCheck(): void {
  const today = new Date().toISOString().slice(0, 10)
  if (today !== day) {
    day = today
    calls = 0
  }
  if (calls >= config.dailyCallBudget) {
    const err = new Error('Daily LLM budget exhausted. Try again tomorrow.') as Error & { status?: number }
    err.status = 503
    throw err
  }
}
export function costGuardRecord(): void {
  calls++
}
export function costGuardStats() {
  return { day, calls, budget: config.dailyCallBudget }
}
