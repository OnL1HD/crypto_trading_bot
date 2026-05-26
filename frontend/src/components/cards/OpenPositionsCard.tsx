import { CardFrame } from './CardFrame'
import type { AsyncState, OpenPositionsResponse } from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'


interface OpenPositionsCardProps {
  positionsState: AsyncState<OpenPositionsResponse>
}


function formatNumber(value: number | null | undefined, digits = 4): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}


export function OpenPositionsCard({ positionsState }: OpenPositionsCardProps) {
  const positions = positionsState.data?.positions ?? []

  return (
    <CardFrame title="Open Positions" subtitle="System-tracked demo positions">
      {positionsState.loading ? <p className="state-text">Loading open positions...</p> : null}
      {!positionsState.loading && positionsState.error ? (
        <p className="state-text state-text--error">{positionsState.error}</p>
      ) : null}

      {!positionsState.loading && !positionsState.error ? (
        positions.length > 0 ? (
          <div className="execution-list">
            {positions.map((position) => (
              <div className="execution-list__row" key={position.trade_id}>
                <div>
                  <span className="metric-label">{position.direction}</span>
                  <strong>{position.symbol}</strong>
                </div>
                <div>
                  <span className="metric-label">Qty</span>
                  <strong>{formatNumber(position.quantity, 5)}</strong>
                </div>
                <div>
                  <span className="metric-label">Leverage</span>
                  <strong>{formatNumber(position.leverage, 0)}x</strong>
                </div>
                <div>
                  <span className="metric-label">Entry</span>
                  <strong>{formatNumber(position.entry_price, 2)}</strong>
                </div>
                <div>
                  <span className="metric-label">Stop / TP</span>
                  <strong>{`${formatNumber(position.stop_loss, 2)} / ${formatNumber(position.take_profit, 2)}`}</strong>
                </div>
                <div>
                  <span className="metric-label">Opened</span>
                  <strong>{formatUtcTimestamp(position.entry_time)}</strong>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="placeholder-state">
            <span className="status-pill status-pill--muted">No open positions</span>
            <p>The system has not recorded any open demo trades yet.</p>
          </div>
        )
      ) : null}
    </CardFrame>
  )
}
