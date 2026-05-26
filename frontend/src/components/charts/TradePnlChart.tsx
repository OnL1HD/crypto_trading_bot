import { useMemo, useState, type MouseEvent } from 'react'
import type { TradeRecord } from '../../types/api'
import { formatUtcMonthDayTime } from '../../utils/time'

type PnlView = 'usdt' | 'percent'

interface TradePnlChartProps {
  trades: TradeRecord[]
}

interface TradePnlPoint {
  tradeId: string
  timestamp: Date
  realizedPnlUsdt: number
  realizedPnlPercent: number
  direction: TradeRecord['direction']
}

interface HoverPoint {
  index: number
  x: number
  y: number
}

const VIEWBOX_WIDTH = 1200
const VIEWBOX_HEIGHT = 360
const PADDING_TOP = 24
const PADDING_RIGHT = 72
const PADDING_BOTTOM = 42
const PADDING_LEFT = 22

function formatCompactNumber(value: number): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
    notation: 'compact',
  })
}

function formatUsdt(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return `${value >= 0 ? '+' : ''}${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatStatUsdt(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '-- USDT'
  }

  return `${value.toFixed(2)} USDT`
}

function buildTradePnlPoints(trades: TradeRecord[]): TradePnlPoint[] {
  return trades
    .filter((trade) => trade.status === 'CLOSED' && typeof trade.realized_pnl === 'number' && Number.isFinite(trade.realized_pnl))
    .map((trade) => {
      const timestampValue = trade.exit_time ?? trade.entry_time
      const timestamp = new Date(timestampValue)
      if (Number.isNaN(timestamp.getTime())) {
        return null
      }

      const notional = typeof trade.entry_price === 'number' && Number.isFinite(trade.entry_price)
        ? trade.entry_price * trade.quantity
        : null
      const realizedPnlPercent = notional && notional > 0
        ? (trade.realized_pnl! / notional) * 100
        : 0

      return {
        tradeId: trade.trade_id,
        timestamp,
        realizedPnlUsdt: trade.realized_pnl!,
        realizedPnlPercent,
        direction: trade.direction,
      }
    })
    .filter((point): point is TradePnlPoint => point !== null)
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
}

function buildYTicks(minValue: number, maxValue: number): number[] {
  const tickCount = 5
  const range = maxValue - minValue

  if (range === 0) {
    return [minValue - 1, minValue - 0.5, minValue, minValue + 0.5, minValue + 1]
  }

  return Array.from({ length: tickCount }, (_, index) => {
    const ratio = index / (tickCount - 1)
    return maxValue - ratio * range
  })
}

function buildTimeTicks(length: number): number[] {
  if (length === 0) {
    return []
  }

  if (length <= 4) {
    return Array.from({ length }, (_, index) => index)
  }

  const lastIndex = length - 1
  return Array.from(new Set([
    0,
    Math.floor(lastIndex * 0.33),
    Math.floor(lastIndex * 0.66),
    lastIndex,
  ]))
}

function formatAxisValue(value: number, view: PnlView): string {
  return view === 'usdt' ? formatCompactNumber(value) : `${value.toFixed(1)}%`
}

function valueLabel(view: PnlView, value: number): string {
  return view === 'usdt' ? formatUsdt(value) : formatPercent(value)
}

function linePath(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) {
    return ''
  }

  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

export function TradePnlChart({ trades }: TradePnlChartProps) {
  const [view, setView] = useState<PnlView>('usdt')
  const [hoverPoint, setHoverPoint] = useState<HoverPoint | null>(null)

  const points = useMemo(() => buildTradePnlPoints(trades), [trades])

  const values = points.map((point) => view === 'usdt' ? point.realizedPnlUsdt : point.realizedPnlPercent)
  const minRaw = values.length > 0 ? Math.min(...values, 0) : -1
  const maxRaw = values.length > 0 ? Math.max(...values, 0) : 1
  const rangePadding = Math.max((maxRaw - minRaw) * 0.14, 0.5)
  const minValue = minRaw - rangePadding
  const maxValue = maxRaw + rangePadding
  const valueRange = maxValue - minValue || 1

  const chartWidth = VIEWBOX_WIDTH - PADDING_LEFT - PADDING_RIGHT
  const chartHeight = VIEWBOX_HEIGHT - PADDING_TOP - PADDING_BOTTOM
  const zeroY = PADDING_TOP + ((maxValue - 0) / valueRange) * chartHeight
  const xStep = points.length > 0 ? chartWidth / points.length : 0
  const barWidth = Math.max(6, Math.min(30, xStep * 0.44))

  const mapX = (index: number) => PADDING_LEFT + index * xStep + xStep / 2
  const mapY = (value: number) => PADDING_TOP + ((maxValue - value) / valueRange) * chartHeight

  const pathPoints = points.map((point, index) => ({
    x: mapX(index),
    y: mapY(view === 'usdt' ? point.realizedPnlUsdt : point.realizedPnlPercent),
  }))

  const hoverTrade = hoverPoint ? points[hoverPoint.index] : points[points.length - 1] ?? null
  const hoverValue = hoverTrade
    ? (view === 'usdt' ? hoverTrade.realizedPnlUsdt : hoverTrade.realizedPnlPercent)
    : null
  const latestTrade = points[points.length - 1] ?? null
  const latestPnlUsdt = latestTrade?.realizedPnlUsdt ?? null

  const netUsdt = points.reduce((total, point) => total + point.realizedPnlUsdt, 0)
  const netPercent = points.reduce((total, point) => total + point.realizedPnlPercent, 0)
  const winningTrades = points.filter((point) => point.realizedPnlUsdt > 0).length
  const losingTrades = points.filter((point) => point.realizedPnlUsdt < 0).length
  const winRate = points.length > 0 ? (winningTrades / points.length) * 100 : null
  const yTicks = buildYTicks(minValue, maxValue)
  const timeTicks = buildTimeTicks(points.length)
  const chartPath = linePath(pathPoints)

  const onMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    if (points.length === 0) {
      setHoverPoint(null)
      return
    }

    const rect = event.currentTarget.getBoundingClientRect()
    if (rect.width <= 0) {
      setHoverPoint(null)
      return
    }

    const ratioX = (event.clientX - rect.left) / rect.width
    const viewboxX = ratioX * VIEWBOX_WIDTH
    const clampedX = Math.min(Math.max(viewboxX, PADDING_LEFT), VIEWBOX_WIDTH - PADDING_RIGHT)
    const localX = Math.min(Math.max(clampedX - PADDING_LEFT, 0), chartWidth)
    const rawIndex = Math.floor(localX / Math.max(xStep, 1))
    const index = Math.min(Math.max(rawIndex, 0), points.length - 1)
    const value = values[index] ?? 0

    setHoverPoint({
      index,
      x: mapX(index),
      y: mapY(value),
    })
  }

  if (points.length === 0) {
    return (
      <section className="chart-shell trade-pnl-chart" aria-label="Realized PnL chart">
        <header className="chart-shell__header">
          <div className="chart-shell__headline-row">
          <div>
            <div className="trade-pnl-chart__title-row">
              <h2>Realized PnL</h2>
              <span className="trade-pnl-chart__title-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16">
                  <path d="M3 10.8 5.6 8.2l1.8 1.8L11.8 5.6" />
                  <path d="M10.2 5.6h1.6v1.6" />
                </svg>
              </span>
            </div>
            <p>Closed trades will populate the chart once realized outcomes are available.</p>
          </div>
            <div className="chart-timeframe-row" role="group" aria-label="PnL metric selector">
              <button type="button" className="chart-timeframe-btn chart-timeframe-btn--active">USDT</button>
              <button type="button" className="chart-timeframe-btn">%</button>
            </div>
          </div>
        </header>
        <div className="line-chart-canvas trade-pnl-chart__canvas">
          <p className="chart-state">No closed trades with realized PnL are available yet.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="chart-shell trade-pnl-chart" aria-label="Realized PnL chart">
      <header className="chart-shell__header">
        <div className="chart-shell__headline-row">
          <div>
            <div className="trade-pnl-chart__title-row">
              <h2>Realized PnL</h2>
              <span className="trade-pnl-chart__title-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16">
                  <path d="M3 10.8 5.6 8.2l1.8 1.8L11.8 5.6" />
                  <path d="M10.2 5.6h1.6v1.6" />
                </svg>
              </span>
            </div>
            <p>Closed trade outcomes plotted over time for the currently stored history.</p>
          </div>
          <div className="chart-timeframe-row" role="group" aria-label="PnL metric selector">
            <button
              type="button"
              className={`chart-timeframe-btn ${view === 'usdt' ? 'chart-timeframe-btn--active' : ''}`}
              onClick={() => setView('usdt')}
            >
              USDT
            </button>
            <button
              type="button"
              className={`chart-timeframe-btn ${view === 'percent' ? 'chart-timeframe-btn--active' : ''}`}
              onClick={() => setView('percent')}
            >
              %
            </button>
          </div>
        </div>

        <div className="trade-pnl-chart__stat-grid">
          <article className="trade-pnl-chart__stat-card trade-pnl-chart__stat-card--latest">
            <div className="trade-pnl-chart__stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M4 4.2 8 8l4-3.8" />
                <path d="M8 8 4 11.8" />
                <path d="M8 8 12 11.8" />
              </svg>
            </div>
            <div>
              <span>Latest PnL</span>
              <strong className={latestPnlUsdt !== null && latestPnlUsdt < 0 ? 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--down' : 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--up'}>
                {formatStatUsdt(latestPnlUsdt)}
              </strong>
            </div>
          </article>

          <article className="trade-pnl-chart__stat-card trade-pnl-chart__stat-card--count">
            <div className="trade-pnl-chart__stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M5 3.5h6" />
                <path d="M8 3.5v2.2" />
                <path d="M4.2 6.5h7.6" />
                <circle cx="8" cy="9" r="3.3" />
              </svg>
            </div>
            <div>
              <span>Closed Trades</span>
              <strong className="trade-pnl-chart__stat-value">{points.length}</strong>
            </div>
          </article>

          <article className="trade-pnl-chart__stat-card trade-pnl-chart__stat-card--winrate">
            <div className="trade-pnl-chart__stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M3.5 11.8 6.2 9.1l1.8 1.8 4.5-5" />
                <path d="M10.8 5.9H13v2.2" />
              </svg>
            </div>
            <div>
              <span>Win Rate</span>
              <strong className="trade-pnl-chart__stat-value trade-pnl-chart__stat-value--up">{winRate === null ? '--' : `${winRate.toFixed(1)}%`}</strong>
            </div>
          </article>

          <article className="trade-pnl-chart__stat-card trade-pnl-chart__stat-card--summary">
            <div>
              <span>Total Realized PnL</span>
              <strong className={netUsdt < 0 ? 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--down' : 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--up'}>
                {formatStatUsdt(netUsdt)}
              </strong>
            </div>
          </article>

          <article className="trade-pnl-chart__stat-card trade-pnl-chart__stat-card--summary">
            <div>
              <span>Net %</span>
              <strong className={netPercent < 0 ? 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--down' : 'trade-pnl-chart__stat-value trade-pnl-chart__stat-value--up'}>
                {formatPercent(netPercent)}
              </strong>
            </div>
          </article>
        </div>
      </header>

      <div className="line-chart-canvas trade-pnl-chart__canvas">
        <svg
          className="line-chart-svg trade-pnl-chart__svg"
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          role="img"
          aria-label="Realized profit and loss history"
          onMouseMove={onMouseMove}
          onMouseLeave={() => setHoverPoint(null)}
        >
          <g className="line-chart-grid">
            {yTicks.map((tick) => {
              const y = mapY(tick)
              return <line key={`pnl-grid-${tick.toFixed(2)}`} x1={PADDING_LEFT} x2={VIEWBOX_WIDTH - PADDING_RIGHT} y1={y} y2={y} />
            })}
          </g>

          <line className="trade-pnl-chart__zero-line" x1={PADDING_LEFT} x2={VIEWBOX_WIDTH - PADDING_RIGHT} y1={zeroY} y2={zeroY} />

          {yTicks.map((tick) => {
            const y = mapY(tick)
            return (
              <text key={`pnl-label-${tick.toFixed(2)}`} className="chart-axis-label" x={VIEWBOX_WIDTH - PADDING_RIGHT + 8} y={y + 4} textAnchor="start">
                {formatAxisValue(tick, view)}
              </text>
            )
          })}

          {timeTicks.map((index) => {
            const point = points[index]
            return (
              <text key={`pnl-time-${point.tradeId}`} className="chart-axis-label" x={mapX(index)} y={VIEWBOX_HEIGHT - 16} textAnchor="middle">
                {formatUtcMonthDayTime(point.timestamp, false)}
              </text>
            )
          })}

          {chartPath ? <path className="trade-pnl-chart__line" d={chartPath} /> : null}

          {points.map((point, index) => {
            const value = view === 'usdt' ? point.realizedPnlUsdt : point.realizedPnlPercent
            const x = mapX(index)
            const y = mapY(value)
            const barTop = Math.min(y, zeroY)
            const barHeight = Math.max(2, Math.abs(y - zeroY))
            const positive = value >= 0
            const isActive = hoverPoint?.index === index

            return (
              <g key={point.tradeId} className={isActive ? 'trade-pnl-chart__point trade-pnl-chart__point--active' : 'trade-pnl-chart__point'}>
                <rect
                  className={positive ? 'trade-pnl-chart__bar trade-pnl-chart__bar--up' : 'trade-pnl-chart__bar trade-pnl-chart__bar--down'}
                  x={x - barWidth / 2}
                  y={barTop}
                  width={barWidth}
                  height={barHeight}
                  rx={3}
                />
                <circle
                  className={positive ? 'trade-pnl-chart__dot trade-pnl-chart__dot--up' : 'trade-pnl-chart__dot trade-pnl-chart__dot--down'}
                  cx={x}
                  cy={y}
                  r={isActive ? 5.5 : 4.25}
                />
              </g>
            )
          })}

          {hoverPoint && hoverTrade ? (
            <>
              <line className="chart-hover-line" x1={hoverPoint.x} x2={hoverPoint.x} y1={PADDING_TOP} y2={VIEWBOX_HEIGHT - PADDING_BOTTOM} />
              <line className="chart-hover-line" x1={PADDING_LEFT} x2={VIEWBOX_WIDTH - PADDING_RIGHT} y1={hoverPoint.y} y2={hoverPoint.y} />
              <text className="chart-hover-price-label" x={VIEWBOX_WIDTH - PADDING_RIGHT + 8} y={hoverPoint.y + 4} textAnchor="start">
                {hoverValue === null ? '--' : valueLabel(view, hoverValue)}
              </text>
              <text className="chart-hover-time-label" x={hoverPoint.x} y={VIEWBOX_HEIGHT - 6} textAnchor="middle">
                {formatUtcMonthDayTime(hoverTrade.timestamp)}
              </text>
            </>
          ) : null}

          <text className="chart-axis-title" x={VIEWBOX_WIDTH - PADDING_RIGHT + 8} y={14} textAnchor="start">
            {view === 'usdt' ? 'USDT' : 'Return %'}
          </text>
        </svg>
      </div>

      <div className="trade-pnl-chart__footer-markers" aria-label="Trade outcome markers">
        <span className="trade-pnl-chart__footer-marker trade-pnl-chart__footer-marker--up">
          <i aria-hidden="true" />
          Profitable
          <strong>{winningTrades}</strong>
        </span>
        <span className="trade-pnl-chart__footer-marker trade-pnl-chart__footer-marker--down">
          <i aria-hidden="true" />
          Losing
          <strong>{losingTrades}</strong>
        </span>
        <span className="trade-pnl-chart__footer-marker trade-pnl-chart__footer-marker--net">
          Net PnL
          <strong className={netUsdt < 0 ? 'trade-pnl-chart__footer-value trade-pnl-chart__footer-value--down' : 'trade-pnl-chart__footer-value trade-pnl-chart__footer-value--up'}>{formatStatUsdt(netUsdt)}</strong>
        </span>
      </div>

      <div className="trade-pnl-chart__orbit" aria-hidden="true">
        <svg viewBox="0 0 88 56">
          <path className="trade-pnl-chart__orbit-ring" d="M8 40.5c0-10.5 17.1-19 38.2-19 8.8 0 17 1.5 23.7 4.1 6.3 2.5 10.3 6 10.3 9.9 0 10.5-17.1 19-38.2 19S8 51 8 40.5Z" />
          <path className="trade-pnl-chart__orbit-swoosh" d="M12.5 47.5c8.1 4.2 20.2 6.7 33.6 6.7 14.8 0 28-3 36-8.1" />
          <circle className="trade-pnl-chart__orbit-core" cx="42" cy="39.5" r="5.4" />
          <circle className="trade-pnl-chart__orbit-dot trade-pnl-chart__orbit-dot--one" cx="63" cy="27" r="2.1" />
          <circle className="trade-pnl-chart__orbit-dot trade-pnl-chart__orbit-dot--two" cx="73" cy="18.5" r="1.8" />
        </svg>
      </div>
    </section>
  )
}
