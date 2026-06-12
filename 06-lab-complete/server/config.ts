/**
 * Centralized config — 12-Factor: mọi thứ đọc từ environment variables.
 * Không hardcode secret; fail-fast nếu thiếu config bắt buộc ở production.
 */
import 'dotenv/config'

function num(v: string | undefined, def: number): number {
  const n = Number(v)
  return Number.isFinite(n) && v !== undefined && v !== '' ? n : def
}

export const config = {
  // Server
  env: process.env.ENVIRONMENT ?? process.env.NODE_ENV ?? 'development',
  port: num(process.env.PORT, 8787),

  // App
  appName: process.env.APP_NAME || 'VinWonders AI Scheduler',
  appVersion: process.env.APP_VERSION || '1.0.0',

  // LLM (Gemini)
  geminiApiKey: process.env.GEMINI_API_KEY ?? '',
  geminiModel: process.env.GEMINI_MODEL || 'gemini-2.5-flash',

  // Security
  // AGENT_API_KEY: nếu đặt → bắt buộc header X-API-Key trên /api/plan. Bỏ trống → endpoint public (frontend gọi trực tiếp).
  agentApiKey: process.env.AGENT_API_KEY ?? '',
  allowedOrigins: (process.env.ALLOWED_ORIGINS ?? '*').split(',').map((s) => s.trim()).filter(Boolean),

  // Rate limit & cost guard
  rateLimitPerMinute: num(process.env.RATE_LIMIT_PER_MINUTE, 20),
  dailyCallBudget: num(process.env.DAILY_CALL_BUDGET, 1000), // số lần gọi LLM tối đa / ngày
}

/** Fail-fast: trả về danh sách warning; ném lỗi nếu thiếu config bắt buộc ở production. */
export function validateConfig(): string[] {
  const warnings: string[] = []
  const isProd = config.env === 'production'

  if (!config.geminiApiKey) {
    if (isProd) throw new Error('GEMINI_API_KEY must be set in production!')
    warnings.push('GEMINI_API_KEY chưa đặt — /api/plan sẽ lỗi cho tới khi cấu hình.')
  }
  if (isProd && config.allowedOrigins.includes('*')) {
    warnings.push('ALLOWED_ORIGINS=* trong production — nên giới hạn domain frontend thật.')
  }
  return warnings
}
