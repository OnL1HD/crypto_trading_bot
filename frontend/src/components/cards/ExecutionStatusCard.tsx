import { CardFrame } from './CardFrame'
import type {
  AsyncState,
  ExecutionStatusResponse,
} from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'


interface ExecutionStatusCardProps {
  executionState: AsyncState<ExecutionStatusResponse>
}


type StatusTone = 'ok' | 'warn' | 'danger' | 'muted'

interface StatusPresentation {
  eyebrow: string
  headline: string
  summary: string
  gate: string
  tone: StatusTone
}


function titleCase(text: string | null | undefined): string {
  if (!text) {
    return '--'
  }

  return text
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function getDisplayedLeverage(data: ExecutionStatusResponse | null): string {
  const openPositionLeverage = data?.latest_execution?.position_direction && data.latest_execution.success
    ? data.latest_execution.leverage
    : null
  const latestExecutionLeverage = data?.latest_execution?.leverage
  const leverage = openPositionLeverage ?? latestExecutionLeverage

  if (typeof leverage !== 'number' || !Number.isFinite(leverage)) {
    return '--'
  }

  return `${leverage}x`
}


function getStatusPresentation(data: ExecutionStatusResponse): StatusPresentation {
  if (!data.enabled) {
    return {
      eyebrow: 'Execution offline',
      headline: 'Execution Disabled',
      summary: 'The execution layer is switched off in config, so no new orders can be sent.',
      gate: 'Disabled in config',
      tone: 'muted',
    }
  }

  if (!data.demo_api_configured) {
    return {
      eyebrow: 'Setup required',
      headline: 'Credentials Missing',
      summary: 'Execution is enabled, but demo API credentials are not available to the backend.',
      gate: 'Missing demo credentials',
      tone: 'danger',
    }
  }

  if (!data.demo_trading_enabled) {
    return {
      eyebrow: 'Config blocked',
      headline: 'Demo Trading Off',
      summary: 'The execution service is configured, but demo trading is not enabled for order placement.',
      gate: 'Demo trading flag off',
      tone: 'warn',
    }
  }

  if (data.open_positions_count > 0) {
    return {
      eyebrow: 'Live management',
      headline: 'Managing Open Position',
      summary: 'Execution is active and currently tracking at least one open demo position.',
      gate: 'Position management active',
      tone: 'ok',
    }
  }

  return {
    eyebrow: 'Execution live',
    headline: 'Ready to Execute',
    summary: 'Demo execution is armed and waiting for the next approved action from the pipeline.',
    gate: 'Ready',
    tone: 'ok',
  }
}


function getLatestActionLabel(data: ExecutionStatusResponse | null): string {
  const latest = data?.latest_execution
  if (!latest) {
    return 'No recent execution activity'
  }

  const signalLabel = titleCase(latest.signal_type)
  const statusLabel = titleCase(latest.status)
  if (signalLabel === '--') {
    return statusLabel
  }

  return `${signalLabel} · ${statusLabel}`
}


function getLatestDetailLabel(data: ExecutionStatusResponse | null): string {
  const latest = data?.latest_execution
  if (!latest) {
    return 'No execution attempts have been recorded yet.'
  }

  if (latest.error_message) {
    return latest.error_message
  }

  if (latest.exchange_response_message) {
    return latest.exchange_response_message
  }

  return 'Latest execution completed without a diagnostic message.'
}


export function ExecutionStatusCard({ executionState }: ExecutionStatusCardProps) {
  const data = executionState.data
  const statusPresentation = data ? getStatusPresentation(data) : null

  return (
    <CardFrame title="Execution Status">
      {executionState.loading ? <p className="state-text">Loading execution status...</p> : null}
      {!executionState.loading && executionState.error ? (
        <p className="state-text state-text--error">{executionState.error}</p>
      ) : null}

      {!executionState.loading && !executionState.error && data && statusPresentation ? (
        <>
          <div className="execution-status-card__hero">
            <span className={`status-pill status-pill--${statusPresentation.tone}`}>{statusPresentation.eyebrow}</span>
            <div className="execution-status-card__hero-copy">
              <h3>{statusPresentation.headline}</h3>
            </div>
          </div>

          <div className="execution-status-card__activity-grid">
            <article className="execution-status-card__activity-tile">
              <span className="metric-label">Last action</span>
              <strong>{getLatestActionLabel(data)}</strong>
            </article>
            <article className="execution-status-card__activity-tile">
              <span className="metric-label">Last updated</span>
              <strong>{formatUtcTimestamp(data.latest_execution?.attempted_at)}</strong>
            </article>
            <article className="execution-status-card__activity-tile execution-status-card__activity-tile--wide">
              <span className="metric-label">Latest detail</span>
              <strong>{getLatestDetailLabel(data)}</strong>
            </article>
          </div>

          <div className="execution-status-card__metrics-grid">
            <article className="execution-status-card__metric-tile">
              <span className="metric-label">Open positions</span>
              <strong>{data.open_positions_count} / {data.max_open_positions}</strong>
            </article>
            <article className="execution-status-card__metric-tile">
              <span className="metric-label">Leverage</span>
              <strong>{getDisplayedLeverage(data)}</strong>
            </article>
            <article className="execution-status-card__metric-tile execution-status-card__metric-tile--gate">
              <span className="metric-label">Current gate</span>
              <strong>{statusPresentation.gate}</strong>
            </article>
          </div>
        </>
      ) : null}
    </CardFrame>
  )
}
