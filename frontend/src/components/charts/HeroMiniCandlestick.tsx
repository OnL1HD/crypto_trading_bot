import { useMemo, useState, type MouseEvent } from 'react'
import type { AsyncState, MarketCandlesResponse } from '../../types/api'
import { formatUtcTime, formatUtcTimestamp } from '../../utils/time'

interface HeroMiniCandlestickProps {
  candlesState: AsyncState<MarketCandlesResponse>
  candleLimit?: number
}

interface MiniCandle {
  openTime: number
  open: number
  high: number
  low: number
  close: number
}

const VIEWBOX_WIDTH = 760
const VIEWBOX_HEIGHT = 360
const PADDING_TOP = 16
const PADDING_RIGHT = 16
const PADDING_BOTTOM = 42
const PADDING_LEFT = 64

function formatPrice(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatAxisTime(timestamp: number): string {
  return formatUtcTime(timestamp)
}

function buildYTicks(minPrice: number, maxPrice: number): number[] {
  const tickCount = 4
  const range = maxPrice - minPrice

  if (range === 0) {
    return [minPrice - 1, minPrice, minPrice + 1, minPrice + 2]
  }

  return Array.from({ length: tickCount }, (_, idx) => {
    const ratio = idx / (tickCount - 1)
    return maxPrice - ratio * range
  })
}

function parseCandles(response: MarketCandlesResponse | null): MiniCandle[] {
  if (!response || response.candles.length === 0) {
    return []
  }

  const parsed = response.candles
    .map((candle) => {
      const openTime = new Date(candle.open_time).getTime()
      if (
        !Number.isFinite(openTime) ||
        typeof candle.open !== 'number' ||
        !Number.isFinite(candle.open) ||
        typeof candle.high !== 'number' ||
        !Number.isFinite(candle.high) ||
        typeof candle.low !== 'number' ||
        !Number.isFinite(candle.low) ||
        typeof candle.close !== 'number' ||
        !Number.isFinite(candle.close)
      ) {
        return null
      }

      return {
        openTime,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }
    })
    .filter((candle): candle is MiniCandle => candle !== null)

  return parsed.sort((a, b) => a.openTime - b.openTime)
}

export function HeroMiniCandlestick({ candlesState, candleLimit = 72 }: HeroMiniCandlestickProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  const candles = useMemo(() => {
    const parsed = parseCandles(candlesState.data)
    return parsed.slice(-Math.max(12, candleLimit))
  }, [candlesState.data, candleLimit])

  if (candlesState.loading || candlesState.error || candles.length === 0) {
    return null
  }

  const candleCount = candles.length
  const chartWidth = VIEWBOX_WIDTH - PADDING_LEFT - PADDING_RIGHT
  const chartHeight = VIEWBOX_HEIGHT - PADDING_TOP - PADDING_BOTTOM
  const low = Math.min(...candles.map((candle) => candle.low))
  const high = Math.max(...candles.map((candle) => candle.high))
  const rangePadding = (high - low) * 0.08
  const minPrice = low - (rangePadding || 1)
  const maxPrice = high + (rangePadding || 1)
  const priceRange = maxPrice - minPrice

  const xStep = chartWidth / candleCount
  const candleBodyWidth = Math.max(2, Math.min(8, xStep * 0.58))
  const wickWidth = Math.max(1, Math.min(2, xStep * 0.14))

  const mapX = (idx: number) => PADDING_LEFT + idx * xStep + xStep / 2
  const mapY = (price: number) => PADDING_TOP + ((maxPrice - price) / priceRange) * chartHeight

  const yTicks = buildYTicks(minPrice, maxPrice)
  const lastIndex = candleCount - 1
  const xTickIndexes = lastIndex <= 0 ? [0] : Array.from(new Set([0, Math.floor(lastIndex * 0.5), lastIndex]))

  const hoveredCandle =
    hoverIndex !== null && hoverIndex >= 0 && hoverIndex < candleCount ? candles[hoverIndex] : null

  const onMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    if (rect.width <= 0) {
      setHoverIndex(null)
      return
    }

    const ratio = (event.clientX - rect.left) / rect.width
    const viewboxX = ratio * VIEWBOX_WIDTH
    const localX = Math.min(Math.max(viewboxX - PADDING_LEFT, 0), chartWidth)
    const rawIndex = Math.floor(localX / Math.max(xStep, 1))
    const index = Math.min(Math.max(rawIndex, 0), candleCount - 1)
    setHoverIndex(index)
  }

  return (
    <div className="hero-mini-chart-shell">
      <svg
        className="hero-mini-chart-svg"
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-label="Mini BTCUSDT candlestick chart"
        onMouseMove={onMouseMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <g className="hero-mini-chart-grid">
          {yTicks.map((tick) => {
            const y = mapY(tick)
            return <line key={`mini-y-grid-${tick.toFixed(2)}`} x1={PADDING_LEFT} x2={VIEWBOX_WIDTH - PADDING_RIGHT} y1={y} y2={y} />
          })}
        </g>

        <g className="hero-mini-chart-axis">
          <line x1={PADDING_LEFT} x2={PADDING_LEFT} y1={PADDING_TOP} y2={VIEWBOX_HEIGHT - PADDING_BOTTOM} />
          <line
            x1={PADDING_LEFT}
            x2={VIEWBOX_WIDTH - PADDING_RIGHT}
            y1={VIEWBOX_HEIGHT - PADDING_BOTTOM}
            y2={VIEWBOX_HEIGHT - PADDING_BOTTOM}
          />
        </g>

        {yTicks.map((tick) => {
          const y = mapY(tick)
          return (
            <text key={`mini-y-label-${tick.toFixed(2)}`} className="hero-mini-chart-axis-label" x={PADDING_LEFT - 8} y={y + 4} textAnchor="end">
              {formatPrice(tick)}
            </text>
          )
        })}

        {xTickIndexes.map((idx) => {
          const x = mapX(idx)
          return (
            <text key={`mini-x-label-${idx}`} className="hero-mini-chart-axis-label" x={x} y={VIEWBOX_HEIGHT - 14} textAnchor="middle">
              {formatAxisTime(candles[idx].openTime)}
            </text>
          )
        })}

        {candles.map((candle, idx) => {
          const x = mapX(idx)
          const openY = mapY(candle.open)
          const closeY = mapY(candle.close)
          const highY = mapY(candle.high)
          const lowY = mapY(candle.low)
          const bodyTop = Math.min(openY, closeY)
          const bodyHeight = Math.max(1, Math.abs(openY - closeY))
          const isUp = candle.close >= candle.open
          const isHovered = idx === hoverIndex
          const candleClass = isUp ? 'hero-mini-chart-candle--up' : 'hero-mini-chart-candle--down'

          return (
            <g key={`${candle.openTime}-${idx}`} className={`${candleClass} ${isHovered ? 'hero-mini-chart-candle--hovered' : ''}`}>
              <line x1={x} x2={x} y1={highY} y2={lowY} strokeWidth={wickWidth} />
              <rect x={x - candleBodyWidth / 2} y={bodyTop} width={candleBodyWidth} height={bodyHeight} rx={1.4} />
            </g>
          )
        })}

        {hoveredCandle ? (
          <line
            className="hero-mini-chart-hover-line"
            x1={mapX(hoverIndex as number)}
            x2={mapX(hoverIndex as number)}
            y1={PADDING_TOP}
            y2={VIEWBOX_HEIGHT - PADDING_BOTTOM}
          />
        ) : null}
      </svg>

      {hoveredCandle ? (
        <div className="hero-mini-chart-tooltip" role="status">
          <span>{formatUtcTimestamp(hoveredCandle.openTime)}</span>
          <strong>{formatPrice(hoveredCandle.close)} USDT</strong>
          <span>
            O {formatPrice(hoveredCandle.open)} | H {formatPrice(hoveredCandle.high)} | L {formatPrice(hoveredCandle.low)}
          </span>
        </div>
      ) : null}
    </div>
  )
}
