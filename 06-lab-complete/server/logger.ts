/** Structured JSON logging — dễ parse trong log aggregator (Datadog, Loki, Cloud Logging...). */
type Level = 'info' | 'warn' | 'error'

function emit(level: Level, event: string, extra: Record<string, unknown> = {}) {
  const line = JSON.stringify({ ts: new Date().toISOString(), level, event, ...extra })
  if (level === 'error') console.error(line)
  else console.log(line)
}

export const logger = {
  info: (event: string, extra?: Record<string, unknown>) => emit('info', event, extra),
  warn: (event: string, extra?: Record<string, unknown>) => emit('warn', event, extra),
  error: (event: string, extra?: Record<string, unknown>) => emit('error', event, extra),
}
