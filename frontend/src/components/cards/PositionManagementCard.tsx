import { CardFrame } from './CardFrame'
import type { AsyncState, PositionManagementLatestResponse } from '../../types/api'

interface PositionManagementCardProps {
  positionManagementState: AsyncState<PositionManagementLatestResponse>
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function PositionManagementCard({ positionManagementState }: PositionManagementCardProps) {
  const decision = positionManagementState.data?.decision

  return (
    <CardFrame title="Position Lifecycle" subtitle="Latest deterministic close evaluation">
      {positionManagementState.loading ? <p className="state-text">Loading lifecycle decision...</p> : null}
      {!positionManagementState.loading && positionManagementState.error ? (
        <p className="state-text state-text--error">{positionManagementState.error}</p>
      ) : null}

      {!positionManagementState.loading && !positionManagementState.error ? (
        decision ? (
          <div className="metrics-grid metrics-grid--compact">
            <div>
              <span className="metric-label">Trade</span>
              <strong>{decision.trade_id.slice(0, 10)}</strong>
            </div>
            <div>
              <span className="metric-label">Action</span>
              <strong>{decision.exit_action}</strong>
            </div>
            <div>
              <span className="metric-label">Reason</span>
              <strong>{decision.exit_reason}</strong>
            </div>
            <div>
              <span className="metric-label">Holding minutes</span>
              <strong>{formatNumber(decision.holding_minutes, 1)}</strong>
            </div>
            <div>
              <span className="metric-label">Current price</span>
              <strong>{formatNumber(decision.current_price, 2)}</strong>
            </div>
            <div>
              <span className="metric-label">Stop / TP</span>
              <strong>{`${formatNumber(decision.stop_loss, 2)} / ${formatNumber(decision.take_profit, 2)}`}</strong>
            </div>
            <div>
              <span className="metric-label">Would close</span>
              <strong>{decision.should_execute_close ? 'Yes' : 'No'}</strong>
            </div>
            <div>
              <span className="metric-label">Executed close</span>
              <strong>{decision.executed_close ? 'Yes' : 'No'}</strong>
            </div>
            <div>
              <span className="metric-label">Skip reason</span>
              <strong>{decision.execution_skipped_reason ?? '--'}</strong>
            </div>
          </div>
        ) : (
          <div className="placeholder-state">
            <span className="status-pill status-pill--muted">No lifecycle decisions</span>
            <p>No open positions have been evaluated yet.</p>
          </div>
        )
      ) : null}
    </CardFrame>
  )
}
