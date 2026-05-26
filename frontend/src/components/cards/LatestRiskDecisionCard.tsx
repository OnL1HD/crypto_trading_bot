import type { ReactNode } from 'react'
import { CardFrame } from './CardFrame'
import type { AsyncState, RiskLatestResponse } from '../../types/api'

interface LatestRiskDecisionCardProps {
  riskState: AsyncState<RiskLatestResponse>
}

function LiveBadge() {
  return (
    <span className="card-live-pill">
      <span className="card-live-pill__dot" aria-hidden="true" />
      LIVE
    </span>
  )
}

function MetricIcon({ children }: { children: ReactNode }) {
  return <span className="metric-tile__icon">{children}</span>
}

function MetricTile({
  label,
  value,
  icon,
}: {
  label: string
  value: string
  icon: ReactNode
}) {
  return (
    <div className="metric-tile">
      <div className="metric-tile__topline">
        <MetricIcon>{icon}</MetricIcon>
        <span className="metric-label">{label}</span>
      </div>
      <strong>{value}</strong>
    </div>
  )
}

function formatPrice(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return value.toFixed(2)
}

function riskStateLabel(allowed: boolean): string {
  return allowed ? 'Allowed to execute' : 'Blocked by risk checks'
}

function actionLabel(value: string | undefined): string {
  const labels: Record<string, string> = {
    OPEN_LONG: 'Open long',
    OPEN_SHORT: 'Open short',
    HOLD: 'Hold',
    SKIP: 'Skip',
    CLOSE_LONG: 'Close long',
    CLOSE_SHORT: 'Close short',
    FLIP_TO_LONG: 'Flip to long',
    FLIP_TO_SHORT: 'Flip to short',
  }

  return value ? (labels[value] ?? value.replaceAll('_', ' ')) : '--'
}

function riskReasonLabel(value: string): string {
  const labels: Record<string, string> = {
    RISK_APPROVED: 'All current risk checks passed.',
    NON_EXECUTABLE_ACTION: 'The strategy output is not an executable entry action.',
    SAME_DIRECTION_POSITION_EXISTS: 'A position in the same direction is already open.',
    MAX_OPEN_POSITIONS_REACHED: 'The system is already at the maximum number of open positions.',
    MAX_TOTAL_OPEN_NOTIONAL_EXCEEDED: 'Opening this trade would exceed the total notional risk cap.',
    COOLDOWN_ACTIVE: 'A cooldown is active after a recent entry.',
    STALE_STRATEGY_DECISION: 'The strategy decision is too old to execute safely.',
    MAX_CONSECUTIVE_LOSSES_REACHED: 'Trading is paused because the consecutive loss limit was reached.',
    DAILY_LOSS_LOCK_ACTIVE: 'Trading is locked because the daily realized loss limit was reached.',
  }

  return labels[value] ?? value.replaceAll('_', ' ')
}

function riskReasons(latestRisk: RiskLatestResponse['decision']): string {
  if (!latestRisk || latestRisk.reason_codes.length === 0) {
    return '--'
  }

  return latestRisk.reason_codes.map(riskReasonLabel).join(' ')
}

export function LatestRiskDecisionCard({ riskState }: LatestRiskDecisionCardProps) {
  const latestRisk = riskState.data?.decision

  return (
    <CardFrame
      title="Latest Risk Decision"
      subtitle="Most recent sizing and protection decision"
      className="card-frame--model"
      statusSlot={<LiveBadge />}
    >
      {riskState.loading ? <p className="state-text">Loading latest risk decision...</p> : null}
      {!riskState.loading && riskState.error ? (
        <p className="state-text state-text--error">{riskState.error}</p>
      ) : null}

      {!riskState.loading && !riskState.error ? (
        latestRisk ? (
          <div className="metrics-grid metrics-grid--compact metrics-grid--model">
            <MetricTile
              label="Risk state"
              value={riskStateLabel(latestRisk.allowed)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <path d="M8 2.2 12.3 4v3.2c0 2.7-1.8 5.1-4.3 6.1-2.5-1-4.3-3.4-4.3-6.1V4L8 2.2Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
                </svg>
              }
            />
            <MetricTile
              label="Requested action"
              value={actionLabel(latestRisk.requested_action)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                  <path d="M5.1 8h5.8M8 5.1 10.9 8 8 10.9" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
            />
            <MetricTile
              label="Approved action"
              value={actionLabel(latestRisk.approved_action)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                  <path d="m6.3 8 1.2 1.2 2.2-2.5" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
            />
            <MetricTile
              label="Risk reasons"
              value={riskReasons(latestRisk)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                  <path d="M8 5.1v3.1" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
                  <circle cx="8" cy="11.1" r="0.75" fill="currentColor" />
                </svg>
              }
            />
            <MetricTile
              label="Approved notional"
              value={formatPrice(latestRisk.order_notional_usdt)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <ellipse cx="8" cy="4.4" rx="4.5" ry="1.8" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M3.5 4.4v5.2C3.5 10.6 5.5 12 8 12s4.5-1.4 4.5-2.4V4.4" stroke="currentColor" strokeWidth="1.2" />
                </svg>
              }
            />
            <MetricTile
              label="Approved leverage"
              value={`${latestRisk.approved_leverage}x`}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <path d="M3.2 11.5 6.1 8.6l2 2L12.8 5.8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M10.6 5.8h2.2V8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              }
            />
            <MetricTile
              label="Stop loss"
              value={formatPrice(latestRisk.stop_loss)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                  <path d="M5.1 8h5.8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
                </svg>
              }
            />
            <MetricTile
              label="Take profit"
              value={formatPrice(latestRisk.take_profit)}
              icon={
                <svg viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                  <path d="M8 5.1v5.8M5.1 8h5.8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
                </svg>
              }
            />
          </div>
        ) : (
          <div className="placeholder-state">
            <span className="status-pill status-pill--muted">No risk decision</span>
            <p>{riskState.data?.message ?? 'Risk output is not available yet.'}</p>
          </div>
        )
      ) : null}
    </CardFrame>
  )
}
