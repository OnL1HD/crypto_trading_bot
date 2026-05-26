import { CardFrame } from './CardFrame'

export function BacktestSummaryCard() {
  return (
    <CardFrame title="Backtest Summary" subtitle="Placeholder for upcoming strategy evaluation">
      <div className="placeholder-state">
        <span className="status-pill status-pill--muted">Coming soon</span>
        <p>
          This panel will surface equity curve, win rate, drawdown, and per-regime performance once
          backtest endpoints are added.
        </p>
      </div>
    </CardFrame>
  )
}
