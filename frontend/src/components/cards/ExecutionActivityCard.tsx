import { useState } from 'react'
import { ExecutionAttemptsOverviewChart } from '../charts/ExecutionAttemptsOverviewChart'
import { TradePnlChart } from '../charts/TradePnlChart'
import type {
  AsyncState,
  ExecutionHistoryResponse,
  TradeHistoryResponse,
} from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface ExecutionActivityCardProps {
  executionHistoryState: AsyncState<ExecutionHistoryResponse>
  tradeHistoryState: AsyncState<TradeHistoryResponse>
}

type ActivityView = 'trades' | 'attempts'

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function titleCase(text: string): string {
  return text
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function pnlTone(value: number | null | undefined): 'up' | 'down' | 'neutral' {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'neutral'
  }

  if (value > 0) {
    return 'up'
  }

  if (value < 0) {
    return 'down'
  }

  return 'neutral'
}

export function ExecutionActivityCard({
  executionHistoryState,
  tradeHistoryState,
}: ExecutionActivityCardProps) {
  const [activeView, setActiveView] = useState<ActivityView>('trades')
  const [attemptsVisibleCount, setAttemptsVisibleCount] = useState(10)
  const executions = executionHistoryState.data?.executions ?? []
  const trades = tradeHistoryState.data?.trades ?? []
  const visibleExecutions = executions.slice().reverse().slice(0, attemptsVisibleCount)
  const hasMoreExecutions = executions.length > attemptsVisibleCount
  const canShowLessExecutions = executions.length > 10 && attemptsVisibleCount > 10

  return (
    <section className="execution-activity-board" aria-label="Execution activity board">
      <header className="execution-activity-board__header">
        <div className="execution-activity-board__title-row">
          <h2>Execution Activity</h2>
          <span className="execution-activity-board__title-dot" aria-hidden="true" />
        </div>
        <p>Review recorded trades or raw execution attempts</p>
        <span className="execution-activity-board__header-spark execution-activity-board__header-spark--left" aria-hidden="true" />
      </header>

      <div className="execution-activity-tabs" aria-label="Execution activity views">
        <div className="execution-activity-tabs__group" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'trades'}
            className={`execution-activity-tabs__button ${activeView === 'trades' ? 'execution-activity-tabs__button--active' : ''}`}
            onClick={() => setActiveView('trades')}
          >
            <span className="execution-activity-tabs__icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M2.5 12.5h11" />
                <path d="M4 11V6.8" />
                <path d="M7.2 11V4.6" />
                <path d="M10.4 11V8.2" />
                <path d="M13.2 11V5.7" />
              </svg>
            </span>
            Trade History
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'attempts'}
            className={`execution-activity-tabs__button ${activeView === 'attempts' ? 'execution-activity-tabs__button--active' : ''}`}
            onClick={() => {
              setActiveView('attempts')
              setAttemptsVisibleCount(10)
            }}
          >
            <span className="execution-activity-tabs__icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M3 4h2" />
                <path d="M3 8h2" />
                <path d="M3 12h2" />
                <path d="M7 4h6" />
                <path d="M7 8h6" />
                <path d="M7 12h6" />
              </svg>
            </span>
            Execution Attempts
          </button>
        </div>
        <span className="execution-activity-tabs__rail" aria-hidden="true">
          <span className="execution-activity-tabs__rail-dot" />
        </span>
      </div>

      {activeView === 'trades' ? (
        <div className="execution-activity-board__stack">
          <div className="execution-activity-panel execution-activity-panel--chart">
            <TradePnlChart trades={trades} />
          </div>

          <section className="execution-activity-panel execution-activity-panel--table" aria-label="Trade history table">
            <header className="execution-activity-panel__header execution-activity-panel__header--table">
              <span className="execution-activity-panel__kicker execution-activity-panel__kicker--history">
                <span className="execution-activity-panel__kicker-icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16">
                    <circle cx="8" cy="8" r="5.5" />
                    <path d="M8 5.1v3.2l2.1 1.2" />
                  </svg>
                </span>
                History
              </span>
            </header>

            {tradeHistoryState.loading ? <p className="state-text">Loading trade history...</p> : null}
            {!tradeHistoryState.loading && tradeHistoryState.error ? (
              <p className="state-text state-text--error">{tradeHistoryState.error}</p>
            ) : null}
            {!tradeHistoryState.loading && !tradeHistoryState.error ? (
              trades.length > 0 ? (
                <div className="table-shell execution-activity-board__table-shell execution-activity-board__table-shell--attempts">
                  <table className="data-table execution-activity-board__table execution-activity-board__table--attempts">
                    <thead>
                      <tr>
                        <th>Trade ID</th>
                        <th>Direction</th>
                        <th>Status</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Qty</th>
                        <th>Leverage</th>
                        <th>Realized PnL</th>
                      </tr>
                    </thead>
                      <tbody>
                        {trades.slice().reverse().map((trade) => (
                          <tr key={trade.trade_id}>
                            <td>
                              <span className="execution-activity-board__trade-id">
                                <span className="execution-activity-board__cell-icon execution-activity-board__cell-icon--star" aria-hidden="true">
                                  <svg viewBox="0 0 16 16">
                                    <path d="m8 2.6 1.5 3 3.3.5-2.4 2.3.6 3.3L8 10.2 5 11.7l.6-3.3-2.4-2.3 3.3-.5Z" />
                                  </svg>
                                </span>
                                {trade.trade_id.slice(0, 10)}
                              </span>
                            </td>
                            <td>
                              <span className={`execution-activity-board__direction execution-activity-board__direction--${trade.direction === 'LONG' ? 'long' : 'short'}`}>
                                <span className="execution-activity-board__cell-icon execution-activity-board__cell-icon--arrow" aria-hidden="true">
                                  <svg viewBox="0 0 16 16">
                                    {trade.direction === 'LONG' ? (
                                      <path d="M8 13V4.2M8 4.2 4.8 7.4M8 4.2l3.2 3.2" />
                                    ) : (
                                      <path d="M8 3v8.8M8 11.8l-3.2-3.2M8 11.8l3.2-3.2" />
                                    )}
                                  </svg>
                                </span>
                                {titleCase(trade.direction)}
                              </span>
                            </td>
                            <td>
                              <span className={`execution-activity-board__status execution-activity-board__status--${trade.status.toLowerCase()}`}>
                                <span className="execution-activity-board__status-dot" aria-hidden="true" />
                                {titleCase(trade.status)}
                              </span>
                            </td>
                            <td>{formatNumber(trade.entry_price, 2)}</td>
                            <td>{formatNumber(trade.exit_price, 2)}</td>
                            <td>{formatNumber(trade.quantity, 5)}</td>
                            <td>{formatNumber(trade.leverage, 0)}x</td>
                            <td>
                              <span className={`execution-activity-board__pnl execution-activity-board__pnl--${pnlTone(trade.realized_pnl)}`}>
                                {formatNumber(trade.realized_pnl, 2)} USDT
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                  </table>
                </div>
              ) : (
                <p className="state-text">No trade records stored yet.</p>
              )
            ) : null}
          </section>
        </div>
      ) : (
        <div className="execution-activity-board__stack">
          <div className="execution-activity-panel execution-activity-panel--chart execution-activity-panel--attempts-chart">
            <ExecutionAttemptsOverviewChart executions={executions} />
          </div>

          <section className="execution-activity-panel execution-activity-panel--table" aria-label="Execution attempts table">
            <header className="execution-activity-panel__header execution-activity-panel__header--table">
              <span className="execution-activity-panel__kicker execution-activity-panel__kicker--history">
                <span className="execution-activity-panel__kicker-icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16">
                    <circle cx="8" cy="8" r="5.5" />
                    <path d="M8 5.1v3.2l2.1 1.2" />
                  </svg>
                </span>
                Execution Attempts
              </span>
            </header>

            {executionHistoryState.loading ? <p className="state-text">Loading execution history...</p> : null}
            {!executionHistoryState.loading && executionHistoryState.error ? (
              <p className="state-text state-text--error">{executionHistoryState.error}</p>
            ) : null}
            {!executionHistoryState.loading && !executionHistoryState.error ? (
              executions.length > 0 ? (
                <>
                  <div className="table-shell execution-activity-board__table-shell execution-activity-board__table-shell--attempts">
                    <table className="data-table execution-activity-board__table execution-activity-board__table--attempts">
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Status</th>
                          <th>Signal</th>
                          <th>Direction</th>
                          <th>Notional</th>
                          <th>Leverage</th>
                          <th>Order ID</th>
                          <th>Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visibleExecutions.map((item) => (
                          <tr key={`${item.execution_key}-${item.attempted_at}-${item.status}`}>
                            <td>{formatUtcTimestamp(item.attempted_at)}</td>
                            <td>
                              <span className={`execution-activity-board__status execution-activity-board__status--${item.status.toLowerCase()}`}>
                                <span className="execution-activity-board__status-dot" aria-hidden="true" />
                                {titleCase(item.status)}
                              </span>
                            </td>
                            <td>{item.signal_type}</td>
                            <td>{item.position_direction ? titleCase(item.position_direction) : '--'}</td>
                            <td>{formatNumber(item.order_notional_usdt, 2)} USDT</td>
                            <td>{formatNumber(item.leverage, 0)}x</td>
                            <td>{item.exchange_order_id ?? '--'}</td>
                            <td>{item.error_message ?? item.exchange_response_message ?? '--'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {hasMoreExecutions || canShowLessExecutions ? (
                    <div className="execution-activity-board__load-more-wrap">
                      {hasMoreExecutions ? (
                        <button
                          type="button"
                          className="execution-activity-board__load-more"
                          onClick={() => setAttemptsVisibleCount((current) => current + 10)}
                        >
                          Load more
                          <span className="execution-activity-board__load-more-icon" aria-hidden="true">
                            <svg viewBox="0 0 16 16">
                              <path d="M4 6.2 8 10.2l4-4" />
                            </svg>
                          </span>
                        </button>
                      ) : null}

                      {canShowLessExecutions ? (
                        <button
                          type="button"
                          className="execution-activity-board__load-more execution-activity-board__load-more--less"
                          onClick={() => setAttemptsVisibleCount((current) => Math.max(10, current - 10))}
                        >
                          Show less
                          <span className="execution-activity-board__load-more-icon execution-activity-board__load-more-icon--up" aria-hidden="true">
                            <svg viewBox="0 0 16 16">
                              <path d="M4 9.8 8 5.8l4 4" />
                            </svg>
                          </span>
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="state-text">No execution attempts recorded yet.</p>
              )
            ) : null}
          </section>
        </div>
      )}
    </section>
  )
}
