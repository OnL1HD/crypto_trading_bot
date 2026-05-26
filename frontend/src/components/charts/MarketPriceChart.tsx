import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import type {
  AsyncState,
  MarketCandlesResponse,
  SignalHistoryResponse,
  SignalLatestResponse,
} from '../../types/api'
import { formatUtcMonthDayTime } from '../../utils/time'

interface MarketPriceChartProps {
  candlesState: AsyncState<MarketCandlesResponse>
  signalHistoryState: AsyncState<SignalHistoryResponse>
  signalState: AsyncState<SignalLatestResponse>
}

type ChartTimeframe = '15m' | '1h' | '4h'

interface TimeframeOption {
  value: ChartTimeframe
  label: string
}

interface CandlePoint {
  openTime: Date
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface SignalMarker {
  signalType: 'BUY' | 'SELL' | 'HOLD'
  probabilityUp: number
  generatedAt: string
}

interface HoverPoint {
  x: number
  y: number
}

type IndicatorMode = 'volume' | 'macd' | 'rsi'

interface CandleIndicators {
  macdHistogram: Array<number | null>
  rsi14: Array<number | null>
}

const TIMEFRAME_OPTIONS: TimeframeOption[] = [
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
]

const ZOOM_CANDLE_OPTIONS = [40, 60, 90, 120, 180, 240, 300]

const VIEWBOX_WIDTH = 1200
const VIEWBOX_HEIGHT = 500
const PADDING_TOP = 20
const PADDING_RIGHT = 68
const PADDING_BOTTOM = 32
const PADDING_LEFT = 18
const VOLUME_AREA_HEIGHT = 60

const INDICATOR_MODE_OPTIONS: Array<{ value: IndicatorMode; label: string }> = [
  { value: 'volume', label: 'Volume' },
  { value: 'macd', label: 'MACD' },
  { value: 'rsi', label: 'RSI' },
]

function formatPrice(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
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

function formatCompact(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 2,
    notation: 'compact',
  }).format(value)
}

function formatAxisTime(date: Date, timeframe: ChartTimeframe): string {
  if (timeframe === '15m') {
    return formatUtcMonthDayTime(date)
  }

  return formatUtcMonthDayTime(date, false)
}

function formatPair(symbol: string | undefined): string {
  if (!symbol) {
    return 'BTC/USDT'
  }

  if (symbol.endsWith('USDT') && symbol.length > 4) {
    return `${symbol.slice(0, -4)}/USDT`
  }

  return symbol
}

function parseCandles(response: MarketCandlesResponse | null): CandlePoint[] {
  if (!response || response.candles.length === 0) {
    return []
  }

  const parsed = response.candles
    .map((candle) => {
      const openTime = new Date(candle.open_time)
      if (
        Number.isNaN(openTime.getTime()) ||
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
        volume: typeof candle.volume === 'number' && Number.isFinite(candle.volume) ? candle.volume : 0,
      }
    })
    .filter((candle): candle is CandlePoint => candle !== null)

  return parsed.sort((a, b) => a.openTime.getTime() - b.openTime.getTime())
}

function aggregateCandles(candles: CandlePoint[], timeframe: ChartTimeframe): CandlePoint[] {
  if (timeframe === '15m') {
    return candles
  }

  const bucketMs = timeframe === '1h' ? 60 * 60 * 1000 : 4 * 60 * 60 * 1000
  const grouped = new Map<number, CandlePoint[]>()

  for (const candle of candles) {
    const ts = candle.openTime.getTime()
    const bucketKey = ts - (ts % bucketMs)
    const bucketCandles = grouped.get(bucketKey)

    if (bucketCandles) {
      bucketCandles.push(candle)
    } else {
      grouped.set(bucketKey, [candle])
    }
  }

  const aggregated = Array.from(grouped.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, bucketCandles]) => {
      const first = bucketCandles[0]
      const last = bucketCandles[bucketCandles.length - 1]
      const high = Math.max(...bucketCandles.map((c) => c.high))
      const low = Math.min(...bucketCandles.map((c) => c.low))
      const volume = bucketCandles.reduce((acc, c) => acc + c.volume, 0)

      return {
        openTime: first.openTime,
        open: first.open,
        high,
        low,
        close: last.close,
        volume,
      }
    })

  return aggregated
}

function buildYTicks(minPrice: number, maxPrice: number): number[] {
  const tickCount = 5
  const range = maxPrice - minPrice

  if (range === 0) {
    return [minPrice - 1, minPrice - 0.5, minPrice, minPrice + 0.5, minPrice + 1]
  }

  return Array.from({ length: tickCount }, (_, idx) => {
    const ratio = idx / (tickCount - 1)
    return maxPrice - ratio * range
  })
}

function buildTimeTicks(candles: CandlePoint[]): number[] {
  if (candles.length === 0) {
    return []
  }

  const lastIndex = candles.length - 1
  const raw = [Math.floor(lastIndex * 0.08), Math.floor(lastIndex * 0.34), Math.floor(lastIndex * 0.62), Math.floor(lastIndex * 0.82)]
  return Array.from(new Set(raw))
}

function timeframeDisplay(timeframe: ChartTimeframe): string {
  if (timeframe === '15m') {
    return '15m'
  }
  if (timeframe === '1h') {
    return '1H'
  }
  return '4H'
}

function buildSignalMap(response: SignalHistoryResponse | null): Map<number, SignalMarker> {
  const signalMap = new Map<number, SignalMarker>()
  if (!response || response.signals.length === 0) {
    return signalMap
  }

  for (const signal of response.signals) {
    const ts = new Date(signal.predicted_for_timestamp).getTime()
    if (!Number.isFinite(ts)) {
      continue
    }

    signalMap.set(ts, {
      signalType: signal.signal_type,
      probabilityUp: signal.probability_up,
      generatedAt: signal.generated_at,
    })
  }

  return signalMap
}

function buildLatestSignalMarker(response: SignalLatestResponse | null): [number, SignalMarker] | null {
  if (
    !response ||
    !response.available ||
    response.signal == null ||
    typeof response.signal.probability_up !== 'number' ||
    typeof response.signal.predicted_for_timestamp !== 'string'
  ) {
    return null
  }

  const ts = new Date(response.signal.predicted_for_timestamp).getTime()
  if (!Number.isFinite(ts)) {
    return null
  }

  return [
    ts,
    {
      signalType: response.signal.signal_type,
      probabilityUp: response.signal.probability_up,
      generatedAt: response.signal.generated_at,
    },
  ]
}

function calculateEma(values: number[], period: number): Array<number | null> {
  const alpha = 2 / (period + 1)
  const result: Array<number | null> = Array(values.length).fill(null)

  if (values.length < period) {
    return result
  }

  let sum = 0
  for (let idx = 0; idx < period; idx += 1) {
    sum += values[idx]
  }

  let ema = sum / period
  result[period - 1] = ema

  for (let idx = period; idx < values.length; idx += 1) {
    ema = values[idx] * alpha + ema * (1 - alpha)
    result[idx] = ema
  }

  return result
}

function calculateIndicators(candles: CandlePoint[]): CandleIndicators {
  const closes = candles.map((candle) => candle.close)
  const macdHistogram: Array<number | null> = Array(candles.length).fill(null)
  const rsi14: Array<number | null> = Array(candles.length).fill(null)

  const ema12 = calculateEma(closes, 12)
  const ema26 = calculateEma(closes, 26)
  const macdLine: Array<number | null> = closes.map((_, idx) => {
    if (ema12[idx] === null || ema26[idx] === null) {
      return null
    }
    return ema12[idx] - ema26[idx]
  })

  const validMacdValues = macdLine.filter((value): value is number => value !== null)
  const signalEmaValues = calculateEma(validMacdValues, 9)
  let signalIdx = 0

  for (let idx = 0; idx < macdLine.length; idx += 1) {
    const macdValue = macdLine[idx]
    if (macdValue === null) {
      continue
    }

    const signalValue = signalEmaValues[signalIdx]
    if (signalValue !== null) {
      macdHistogram[idx] = macdValue - signalValue
    }
    signalIdx += 1
  }

  if (closes.length > 14) {
    let gains = 0
    let losses = 0

    for (let idx = 1; idx <= 14; idx += 1) {
      const delta = closes[idx] - closes[idx - 1]
      if (delta >= 0) {
        gains += delta
      } else {
        losses += Math.abs(delta)
      }
    }

    let averageGain = gains / 14
    let averageLoss = losses / 14
    rsi14[14] = averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss)

    for (let idx = 15; idx < closes.length; idx += 1) {
      const delta = closes[idx] - closes[idx - 1]
      const gain = delta > 0 ? delta : 0
      const loss = delta < 0 ? Math.abs(delta) : 0

      averageGain = (averageGain * 13 + gain) / 14
      averageLoss = (averageLoss * 13 + loss) / 14
      rsi14[idx] = averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss)
    }
  }

  return {
    macdHistogram,
    rsi14,
  }
}

function buildLinePath(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) {
    return ''
  }

  return points.map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

export function MarketPriceChart({ candlesState, signalHistoryState, signalState }: MarketPriceChartProps) {
  const [timeframe, setTimeframe] = useState<ChartTimeframe>('15m')
  const [indicatorMode, setIndicatorMode] = useState<IndicatorMode>('volume')
  const [zoomIndex, setZoomIndex] = useState<number>(ZOOM_CANDLE_OPTIONS.length - 1)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const [hoverPoint, setHoverPoint] = useState<HoverPoint | null>(null)
  const [panOffset, setPanOffset] = useState<number>(0)
  const [isDragging, setIsDragging] = useState<boolean>(false)
  const chartCanvasRef = useRef<HTMLDivElement | null>(null)
  const dragStartClientXRef = useRef<number | null>(null)
  const dragStartOffsetRef = useRef<number>(0)

  const parsedCandles = useMemo(() => parseCandles(candlesState.data), [candlesState.data])

  const chartCandles = useMemo(() => {
    const aggregated = aggregateCandles(parsedCandles, timeframe)
    return aggregated.slice(-300)
  }, [parsedCandles, timeframe])

  const visibleTarget = ZOOM_CANDLE_OPTIONS[zoomIndex]
  const visibleCount = Math.min(visibleTarget, chartCandles.length)
  const maxPanOffset = Math.max(chartCandles.length - visibleCount, 0)
  const resolvedPanOffset = Math.min(panOffset, maxPanOffset)

  const visibleCandles = useMemo(() => {
    const endIndex = chartCandles.length - resolvedPanOffset
    const startIndex = Math.max(endIndex - visibleCount, 0)
    return chartCandles.slice(startIndex, endIndex)
  }, [chartCandles, resolvedPanOffset, visibleCount])

  const visibleIndicators = useMemo(() => calculateIndicators(visibleCandles), [visibleCandles])

  const signalMap = useMemo(() => {
    const map = buildSignalMap(signalHistoryState.data)
    const latestMarker = buildLatestSignalMarker(signalState.data)
    if (latestMarker !== null) {
      map.set(latestMarker[0], latestMarker[1])
    }
    return map
  }, [signalHistoryState.data, signalState.data])

  const candleCount = visibleCandles.length
  const pairLabel = formatPair(candlesState.data?.symbol)
  const titleLabel = `${candlesState.data?.symbol ?? 'BTCUSDT'} • ${timeframeDisplay(timeframe)} • Bybit`

  const chartWidth = VIEWBOX_WIDTH - PADDING_LEFT - PADDING_RIGHT
  const chartHeight = VIEWBOX_HEIGHT - PADDING_TOP - PADDING_BOTTOM - VOLUME_AREA_HEIGHT
  const volumeTop = PADDING_TOP + chartHeight + 8
  const volumeBottom = VIEWBOX_HEIGHT - PADDING_BOTTOM

  const minPrice = candleCount > 0 ? Math.min(...visibleCandles.map((c) => c.low)) : 0
  const maxPrice = candleCount > 0 ? Math.max(...visibleCandles.map((c) => c.high)) : 1
  const pricePadding = (maxPrice - minPrice) * 0.05
  const yMin = minPrice - (pricePadding || 1)
  const yMax = maxPrice + (pricePadding || 1)
  const yRange = yMax - yMin
  const maxVolume = candleCount > 0 ? Math.max(...visibleCandles.map((c) => c.volume)) : 0
  const macdValues = visibleIndicators.macdHistogram.filter((value): value is number => value !== null)
  const macdMaxAbs = macdValues.length > 0 ? Math.max(...macdValues.map((value) => Math.abs(value))) : 0

  const xStep = candleCount > 0 ? chartWidth / candleCount : 0
  const candleBodyWidth = Math.max(2, Math.min(12, xStep * 0.62))
  const wickWidth = Math.max(1, Math.min(2, xStep * 0.14))
  const volumeBarWidth = Math.max(2, Math.min(14, xStep * 0.7))

  const mapX = (idx: number) => PADDING_LEFT + idx * xStep + xStep / 2
  const mapY = (price: number) => PADDING_TOP + ((yMax - price) / yRange) * chartHeight

  const yTicks = buildYTicks(yMin, yMax)
  const timeTickIndexes = buildTimeTicks(visibleCandles)
  const hovered = hoverIndex !== null && hoverIndex >= 0 && hoverIndex < visibleCandles.length ? visibleCandles[hoverIndex] : null
  const focusCandle = hovered ?? (candleCount > 0 ? visibleCandles[candleCount - 1] : null)
  const hoverPrice = hoverPoint
    ? yMax - ((hoverPoint.y - PADDING_TOP) / Math.max(chartHeight, 1)) * yRange
    : null

  const firstClose = candleCount > 0 ? visibleCandles[0].close : null
  const lastClose = candleCount > 0 ? visibleCandles[candleCount - 1].close : null
  const delta = typeof firstClose === 'number' && typeof lastClose === 'number' ? lastClose - firstClose : null
  const deltaPct = typeof firstClose === 'number' && typeof lastClose === 'number' && firstClose !== 0
    ? ((lastClose - firstClose) / firstClose) * 100
    : null
  const deltaClass = delta !== null && delta < 0 ? 'chart-delta chart-delta--down' : 'chart-delta chart-delta--up'

  const onMouseMove = (event: MouseEvent<SVGSVGElement>) => {
    if (visibleCandles.length === 0) {
      setHoverIndex(null)
      setHoverPoint(null)
      return
    }

    const rect = event.currentTarget.getBoundingClientRect()
    if (rect.width <= 0) {
      setHoverIndex(null)
      setHoverPoint(null)
      return
    }

    const ratioX = (event.clientX - rect.left) / rect.width
    const ratioY = (event.clientY - rect.top) / rect.height
    const viewboxX = ratioX * VIEWBOX_WIDTH
    const viewboxY = ratioY * VIEWBOX_HEIGHT
    const clampedX = Math.min(Math.max(viewboxX, PADDING_LEFT), VIEWBOX_WIDTH - PADDING_RIGHT)
    const clampedY = Math.min(Math.max(viewboxY, PADDING_TOP), PADDING_TOP + chartHeight)
    const localX = Math.min(Math.max(clampedX - PADDING_LEFT, 0), chartWidth)
    const rawIndex = Math.floor(localX / Math.max(xStep, 1))
    const index = Math.min(Math.max(rawIndex, 0), visibleCandles.length - 1)

    setHoverIndex(index)
    setHoverPoint({ x: clampedX, y: clampedY })
  }

  const onChartWheel = (event: WheelEvent) => {
    event.preventDefault()
    event.stopPropagation()

    if (event.deltaY > 0) {
      setZoomIndex((current) => Math.min(current + 1, ZOOM_CANDLE_OPTIONS.length - 1))
    } else {
      setZoomIndex((current) => Math.max(current - 1, 0))
    }
  }

  const canZoomIn = zoomIndex > 0
  const canZoomOut = zoomIndex < ZOOM_CANDLE_OPTIONS.length - 1
  const signalOverlayError = !signalHistoryState.loading && signalHistoryState.error
    ? signalHistoryState.error
    : (!signalState.loading && signalState.error ? signalState.error : null)
  const visibleSignalCount = useMemo(() => {
    if (timeframe !== '15m') {
      return 0
    }

    return visibleCandles.reduce((count, candle) => {
      const key = candle.openTime.getTime()
      const signal = signalMap.get(key)
      if (signal?.signalType === 'BUY' || signal?.signalType === 'SELL') {
        return count + 1
      }
      return count
    }, 0)
  }, [timeframe, visibleCandles, signalMap])

  const focusSignal = useMemo(() => {
    if (timeframe !== '15m' || focusCandle === null) {
      return null
    }

    return signalMap.get(focusCandle.openTime.getTime()) ?? null
  }, [timeframe, focusCandle, signalMap])

  useEffect(() => {
    const chartCanvas = chartCanvasRef.current
    if (chartCanvas === null) {
      return
    }

    const handleWheel = (event: WheelEvent) => {
      onChartWheel(event)
    }

    chartCanvas.addEventListener('wheel', handleWheel, { passive: false })

    return () => {
      chartCanvas.removeEventListener('wheel', handleWheel)
    }
  }, [])

  useEffect(() => {
    if (!isDragging) {
      return
    }

    const handleWindowMouseUp = () => {
      dragStartClientXRef.current = null
      setIsDragging(false)
    }

    window.addEventListener('mouseup', handleWindowMouseUp)

    return () => {
      window.removeEventListener('mouseup', handleWindowMouseUp)
    }
  }, [isDragging])

  const handleDragStart = (event: MouseEvent<SVGSVGElement>) => {
    if (candleCount === 0) {
      return
    }

    event.preventDefault()
    dragStartClientXRef.current = event.clientX
    dragStartOffsetRef.current = resolvedPanOffset
    setIsDragging(true)
  }

  const handleDragMove = (event: MouseEvent<SVGSVGElement>) => {
    if (!isDragging || dragStartClientXRef.current === null || candleCount === 0) {
      return
    }

    const deltaX = event.clientX - dragStartClientXRef.current
    const candlesShift = Math.round(deltaX / Math.max(xStep, 1))
    const visibleTarget = ZOOM_CANDLE_OPTIONS[zoomIndex]
    const visibleCount = Math.min(visibleTarget, chartCandles.length)
    const maxPanOffset = Math.max(chartCandles.length - visibleCount, 0)
    const nextOffset = Math.min(
      Math.max(dragStartOffsetRef.current + candlesShift, 0),
      maxPanOffset,
    )

    setPanOffset(nextOffset)
    setHoverIndex(null)
    setHoverPoint(null)
  }

  const handleDragEnd = () => {
    dragStartClientXRef.current = null
    setIsDragging(false)
  }

  return (
    <section className="chart-shell" aria-label="Market price chart">
      <header className="chart-shell__header">
        <div className="chart-shell__headline-row">
          <div>
            <h2>{titleLabel}</h2>
          </div>

          <div className="chart-indicator-controls" role="group" aria-label="Indicator mode selector">
            {INDICATOR_MODE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`chart-indicator-btn ${indicatorMode === option.value ? 'chart-indicator-btn--active' : ''}`}
                onClick={() => setIndicatorMode(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="chart-timeframe-row" role="group" aria-label="Chart timeframe selector">
            {TIMEFRAME_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`chart-timeframe-btn ${timeframe === option.value ? 'chart-timeframe-btn--active' : ''}`}
                onClick={() => setTimeframe(option.value)}
              >
                {option.label}
              </button>
            ))}

            <div className="chart-zoom-controls">
              <button
                type="button"
                className="chart-zoom-btn"
                onClick={() => setZoomIndex((current) => Math.max(current - 1, 0))}
                disabled={!canZoomIn}
                aria-label="Zoom in"
              >
                +
              </button>
              <button
                type="button"
                className="chart-zoom-btn"
                onClick={() => setZoomIndex((current) => Math.min(current + 1, ZOOM_CANDLE_OPTIONS.length - 1))}
                disabled={!canZoomOut}
                aria-label="Zoom out"
              >
                -
              </button>
            </div>
          </div>
        </div>

        <div className="chart-shell__stats-row">
          <div className="chart-shell__stats chart-shell__stats--primary">
            <span>O <strong>{formatPrice(focusCandle?.open)}</strong></span>
            <span>H <strong>{formatPrice(focusCandle?.high)}</strong></span>
            <span>L <strong>{formatPrice(focusCandle?.low)}</strong></span>
            <span>C <strong>{formatPrice(focusCandle?.close)}</strong></span>
            <span className={deltaClass}>Δ <strong>{formatPrice(delta)}</strong></span>
            <span className={deltaClass}>% <strong>{deltaPct === null ? '--' : `${deltaPct >= 0 ? '+' : ''}${deltaPct.toFixed(2)}%`}</strong></span>
          </div>

          <div className="chart-shell__stats chart-shell__stats--secondary">
            <span>Signal <strong>{focusSignal?.signalType ?? '--'}</strong></span>
            <span>P(UP) <strong>{focusSignal ? `${(focusSignal.probabilityUp * 100).toFixed(2)}%` : '--'}</strong></span>
            <span>Signals <strong>{timeframe === '15m' ? visibleSignalCount : 0}</strong></span>
            <span>Visible <strong>{Math.min(ZOOM_CANDLE_OPTIONS[zoomIndex], chartCandles.length)}</strong></span>
          </div>
        </div>
      </header>

      <div className="line-chart-canvas" ref={chartCanvasRef}>
        {candlesState.loading ? <p className="chart-state">Loading market candles...</p> : null}
        {!candlesState.loading && candlesState.error ? (
          <p className="chart-state chart-state--error">{candlesState.error}</p>
        ) : null}
        {!candlesState.loading && !candlesState.error && candleCount === 0 ? <p className="chart-state">No candles available for chart display.</p> : null}

        {!candlesState.loading && !candlesState.error && candleCount > 0 ? (
          <>
            <div className="chart-signal-legend chart-signal-legend--overlay" aria-label="Signal legend">
              <span className="chart-signal-legend__item chart-signal-legend__item--up">▲ BUY</span>
              <span className="chart-signal-legend__item chart-signal-legend__item--down">▼ SELL</span>
              {signalOverlayError ? <span className="chart-signal-legend__note state-text--error">Signal overlay: {signalOverlayError}</span> : null}
            </div>

            <svg
              className={`line-chart-svg ${isDragging ? 'line-chart-svg--dragging' : 'line-chart-svg--draggable'}`}
              viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
              role="img"
              aria-label={`${pairLabel} candlestick chart`}
              onMouseDown={handleDragStart}
              onMouseMove={(event) => {
                handleDragMove(event)
                if (!isDragging) {
                  onMouseMove(event)
                }
              }}
              onMouseUp={handleDragEnd}
              onMouseLeave={() => {
                handleDragEnd()
                setHoverIndex(null)
                setHoverPoint(null)
              }}
            >
              <g className="line-chart-grid">
                {yTicks.map((tick) => {
                  const y = mapY(tick)
                  return <line key={`y-grid-${tick.toFixed(2)}`} x1={PADDING_LEFT} x2={VIEWBOX_WIDTH - PADDING_RIGHT} y1={y} y2={y} />
                })}
              </g>

              {yTicks.map((tick) => {
                const y = mapY(tick)
                return (
                  <text key={`y-label-${tick.toFixed(2)}`} className="chart-axis-label" x={VIEWBOX_WIDTH - PADDING_RIGHT + 8} y={y + 4} textAnchor="start">
                    {formatPrice(tick)}
                  </text>
                )
              })}

              {timeTickIndexes.map((idx) => {
                const candle = visibleCandles[idx]
                const x = mapX(idx)
                return (
                  <text key={`x-label-${idx}`} className="chart-axis-label" x={x} y={VIEWBOX_HEIGHT - 16} textAnchor="middle">
                    {formatAxisTime(candle.openTime, timeframe)}
                  </text>
                )
              })}

              {visibleCandles.map((candle, idx) => {
                const x = mapX(idx)
                const openY = mapY(candle.open)
                const closeY = mapY(candle.close)
                const highY = mapY(candle.high)
                const lowY = mapY(candle.low)
                const bodyTop = Math.min(openY, closeY)
                const bodyHeight = Math.max(1, Math.abs(openY - closeY))
                const isUp = candle.close >= candle.open
                const colorClass = isUp ? 'chart-candle chart-candle--up' : 'chart-candle chart-candle--down'
                const isHovered = idx === hoverIndex
                const signal = timeframe === '15m' ? signalMap.get(candle.openTime.getTime()) : undefined
                const showSignal = signal?.signalType === 'BUY' || signal?.signalType === 'SELL'
                const isBuySignal = signal?.signalType === 'BUY'
                const signalY = isBuySignal ? highY - 8 : lowY + 12

                return (
                  <g key={`${candle.openTime.toISOString()}-${idx}`} className={`${colorClass} ${isHovered ? 'chart-candle--hovered' : ''}`}>
                    {indicatorMode === 'volume' && maxVolume > 0 ? (
                      <rect
                        className={`chart-volume-bar ${isUp ? 'chart-volume-bar--up' : 'chart-volume-bar--down'}`}
                        x={x - volumeBarWidth / 2}
                        y={volumeBottom - (candle.volume / maxVolume) * VOLUME_AREA_HEIGHT}
                        width={volumeBarWidth}
                        height={Math.max(2, (candle.volume / maxVolume) * VOLUME_AREA_HEIGHT)}
                        rx={1}
                      />
                    ) : null}
                    <line x1={x} x2={x} y1={highY} y2={lowY} strokeWidth={wickWidth} />
                    <rect x={x - candleBodyWidth / 2} y={bodyTop} width={candleBodyWidth} height={bodyHeight} rx={1.5} />
                    {showSignal ? (
                      <text
                        x={x}
                        y={signalY}
                        textAnchor="middle"
                        className={`chart-signal ${isBuySignal ? 'chart-signal--up' : 'chart-signal--down'}`}
                      >
                        {isBuySignal ? '▲' : '▼'}
                      </text>
                    ) : null}
                  </g>
                )
              })}

              {indicatorMode === 'macd' ? (
                <>
                  <line
                    className="chart-indicator-baseline"
                    x1={PADDING_LEFT}
                    x2={VIEWBOX_WIDTH - PADDING_RIGHT}
                    y1={volumeTop + VOLUME_AREA_HEIGHT / 2}
                    y2={volumeTop + VOLUME_AREA_HEIGHT / 2}
                  />
                  {visibleCandles.map((candle, idx) => {
                    const histogramValue = visibleIndicators.macdHistogram[idx]
                    if (histogramValue === null || macdMaxAbs === 0) {
                      return null
                    }

                    const x = mapX(idx)
                    const zeroY = volumeTop + VOLUME_AREA_HEIGHT / 2
                    const scaledHeight = (Math.abs(histogramValue) / macdMaxAbs) * (VOLUME_AREA_HEIGHT / 2)
                    const isPositive = histogramValue >= 0
                    const barY = isPositive ? zeroY - scaledHeight : zeroY

                    return (
                      <rect
                        key={`macd-${candle.openTime.toISOString()}-${idx}`}
                        className={`chart-macd-bar ${isPositive ? 'chart-macd-bar--up' : 'chart-macd-bar--down'}`}
                        x={x - volumeBarWidth / 2}
                        y={barY}
                        width={volumeBarWidth}
                        height={Math.max(2, scaledHeight)}
                        rx={1}
                      />
                    )
                  })}
                </>
              ) : null}

              {indicatorMode === 'rsi' ? (
                <>
                  {[30, 50, 70].map((level) => {
                    const y = volumeTop + ((100 - level) / 100) * VOLUME_AREA_HEIGHT
                    return (
                      <line
                        key={`rsi-level-${level}`}
                        className={`chart-indicator-baseline ${level === 50 ? 'chart-indicator-baseline--mid' : ''}`}
                        x1={PADDING_LEFT}
                        x2={VIEWBOX_WIDTH - PADDING_RIGHT}
                        y1={y}
                        y2={y}
                      />
                    )
                  })}
                  {(() => {
                    const points = visibleIndicators.rsi14
                      .map((value, idx) => {
                        if (value === null) {
                          return null
                        }
                        return {
                          x: mapX(idx),
                          y: volumeTop + ((100 - value) / 100) * VOLUME_AREA_HEIGHT,
                        }
                      })
                      .filter((point): point is { x: number; y: number } => point !== null)

                    const path = buildLinePath(points)
                    return path ? <path className="chart-rsi-line" d={path} /> : null
                  })()}
                </>
              ) : null}

              {hoverPoint ? (
                <line
                  className="chart-hover-line"
                  x1={hoverPoint.x}
                  x2={hoverPoint.x}
                  y1={PADDING_TOP}
                  y2={VIEWBOX_HEIGHT - PADDING_BOTTOM}
                />
              ) : null}

              {hoverPoint ? (
                  <line
                    className="chart-hover-line"
                    x1={PADDING_LEFT}
                    x2={VIEWBOX_WIDTH - PADDING_RIGHT}
                    y1={hoverPoint.y}
                    y2={hoverPoint.y}
                  />
                ) : null}

              {hoverPoint && hoverPrice !== null ? (
                <text
                  className="chart-hover-price-label"
                  x={VIEWBOX_WIDTH - PADDING_RIGHT + 8}
                  y={hoverPoint.y + 4}
                  textAnchor="start"
                >
                  {formatPrice(hoverPrice)}
                </text>
              ) : null}

              {hovered && hoverPoint ? (
                <text
                  className="chart-hover-time-label"
                  x={hoverPoint.x}
                  y={VIEWBOX_HEIGHT - 6}
                  textAnchor="middle"
                >
                  {formatUtcMonthDayTime(hovered.openTime)}
                </text>
              ) : null}

              {hovered && hoverPoint ? (
                <text
                  className="chart-hover-indicator-label"
                  x={Math.min(hoverPoint.x + 10, VIEWBOX_WIDTH - PADDING_RIGHT - 84)}
                  y={Math.max(volumeTop + 14, Math.min(hoverPoint.y - 10, VIEWBOX_HEIGHT - PADDING_BOTTOM - 10))}
                  textAnchor="start"
                >
                  {indicatorMode === 'volume'
                    ? `Vol ${formatCompact(hovered.volume)}`
                    : indicatorMode === 'macd'
                      ? `MACD ${formatNumber(visibleIndicators.macdHistogram[hoverIndex as number], 5)}`
                      : `RSI ${formatNumber(visibleIndicators.rsi14[hoverIndex as number], 2)}`}
                </text>
              ) : null}

              {lastClose !== null ? (
                <>
                  <line
                    className="chart-last-price-line"
                    x1={PADDING_LEFT}
                    x2={VIEWBOX_WIDTH - PADDING_RIGHT}
                    y1={mapY(lastClose)}
                    y2={mapY(lastClose)}
                  />
                  <text
                    className="chart-last-price-label"
                    x={VIEWBOX_WIDTH - PADDING_RIGHT + 8}
                    y={mapY(lastClose) + 4}
                    textAnchor="start"
                  >
                    {formatPrice(lastClose)}
                  </text>
                </>
              ) : null}

              <text className="chart-axis-title" x={VIEWBOX_WIDTH - PADDING_RIGHT + 8} y={14} textAnchor="start">
                USDT
              </text>
              <text className="chart-axis-title" x={PADDING_LEFT} y={volumeTop + 12} textAnchor="start">
                {indicatorMode === 'volume' ? 'Vol' : indicatorMode === 'macd' ? 'MACD' : 'RSI'}
              </text>
            </svg>

          </>
        ) : null}
      </div>
    </section>
  )
}
