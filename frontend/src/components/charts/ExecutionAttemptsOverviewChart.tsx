import { useMemo, useState } from 'react'
import type { ExecutionAttemptRecord } from '../../types/api'
import { formatUtcMonthDayTime, formatUtcTime } from '../../utils/time'

type AttemptsRange = '24h' | '7d' | '30d'

interface ExecutionAttemptsOverviewChartProps {
  executions: ExecutionAttemptRecord[]
}

interface AttemptBucket {
  key: string
  label: string
  placed: number
  closed: number
}

const VIEWBOX_WIDTH = 1200
const VIEWBOX_HEIGHT = 280
const PADDING_TOP = 26
const PADDING_RIGHT = 4
const PADDING_BOTTOM = 40
const PADDING_LEFT = 4

function floorToHour(date: Date): Date {
  const copy = new Date(date)
  copy.setUTCMinutes(0, 0, 0)
  return copy
}

function floorToDay(date: Date): Date {
  const copy = new Date(date)
  copy.setUTCHours(0, 0, 0, 0)
  return copy
}

function addHours(date: Date, amount: number): Date {
  const copy = new Date(date)
  copy.setUTCHours(copy.getUTCHours() + amount)
  return copy
}

function addDays(date: Date, amount: number): Date {
  const copy = new Date(date)
  copy.setUTCDate(copy.getUTCDate() + amount)
  return copy
}

function buildBuckets(executions: ExecutionAttemptRecord[], range: AttemptsRange): AttemptBucket[] {
  const now = new Date()
  const filtered = executions
    .map((item) => ({ ...item, parsed: new Date(item.attempted_at) }))
    .filter((item) => !Number.isNaN(item.parsed.getTime()))
    .sort((a, b) => a.parsed.getTime() - b.parsed.getTime())

  if (filtered.length === 0) {
    return []
  }

  const isHourly = range === '24h'
  const bucketCount = range === '24h' ? 12 : range === '7d' ? 7 : 10
  const stepHours = range === '24h' ? 2 : 0
  const stepDays = range === '7d' ? 1 : 3
  const latest = filtered[filtered.length - 1]?.parsed ?? now
  const end = isHourly ? floorToHour(latest) : floorToDay(latest)
  const start = isHourly ? addHours(end, -(bucketCount - 1) * stepHours) : addDays(end, -(bucketCount - 1) * stepDays)

  const buckets: AttemptBucket[] = Array.from({ length: bucketCount }, (_, index) => {
    const bucketDate = isHourly ? addHours(start, index * stepHours) : addDays(start, index * stepDays)
    const label = isHourly
      ? formatUtcTime(bucketDate)
      : index === 0 || index === bucketCount - 1
        ? formatUtcMonthDayTime(bucketDate, false)
        : formatUtcMonthDayTime(bucketDate, false)

    return {
      key: bucketDate.toISOString(),
      label,
      placed: 0,
      closed: 0,
    }
  })

  filtered.forEach((item) => {
    if (item.parsed < start) {
      return
    }

    const offsetMs = item.parsed.getTime() - start.getTime()
    const stepMs = isHourly ? stepHours * 60 * 60 * 1000 : stepDays * 24 * 60 * 60 * 1000
    const bucketIndex = Math.min(Math.floor(offsetMs / stepMs), bucketCount - 1)
    const bucket = buckets[bucketIndex]
    if (!bucket) {
      return
    }

    if (item.status === 'placed') {
      bucket.placed += 1
    }
    if (item.status === 'closed') {
      bucket.closed += 1
    }
  })

  return buckets
}

export function ExecutionAttemptsOverviewChart({ executions }: ExecutionAttemptsOverviewChartProps) {
  const [range, setRange] = useState<AttemptsRange>('24h')

  const buckets = useMemo(() => buildBuckets(executions, range), [executions, range])
  const placedTotal = buckets.reduce((total, bucket) => total + bucket.placed, 0)
  const closedTotal = buckets.reduce((total, bucket) => total + bucket.closed, 0)
  const total = placedTotal + closedTotal
  const peak = Math.max(1, ...buckets.flatMap((bucket) => [bucket.placed, bucket.closed]))

  const chartWidth = VIEWBOX_WIDTH - PADDING_LEFT - PADDING_RIGHT
  const chartHeight = VIEWBOX_HEIGHT - PADDING_TOP - PADDING_BOTTOM
  const baselineY = PADDING_TOP + chartHeight / 2
  const xStep = buckets.length > 0 ? chartWidth / buckets.length : 0
  const barScale = (chartHeight / 2 - 10) / peak

  if (buckets.length === 0) {
    return (
      <section className="execution-attempts-chart" aria-label="Execution attempts overview">
        <header className="execution-attempts-chart__header">
          <div className="execution-attempts-chart__title-group">
            <h3>Execution Attempts Overview</h3>
          </div>
          <div className="execution-attempts-chart__range-shell">
            <span className="execution-attempts-chart__range-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <rect x="2.5" y="3.5" width="11" height="10" rx="2" />
                <path d="M5 2.5v2" />
                <path d="M11 2.5v2" />
                <path d="M2.5 6.2h11" />
              </svg>
            </span>
            <select value={range} onChange={(event) => setRange(event.target.value as AttemptsRange)}>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>
        </header>
        <div className="line-chart-canvas execution-attempts-chart__canvas">
          <p className="chart-state">No execution attempts are available yet.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="execution-attempts-chart" aria-label="Execution attempts overview">
      <header className="execution-attempts-chart__header">
        <div className="execution-attempts-chart__title-group">
          <h3>Execution Attempts Overview</h3>
        </div>

        <div className="execution-attempts-chart__summary-row">
          <span className="execution-attempts-chart__summary execution-attempts-chart__summary--placed">
            <i aria-hidden="true" />
            Placed
            <strong>{placedTotal}</strong>
          </span>
          <span className="execution-attempts-chart__summary execution-attempts-chart__summary--closed">
            <i aria-hidden="true" />
            Closed
            <strong>{closedTotal}</strong>
          </span>
          <span className="execution-attempts-chart__summary execution-attempts-chart__summary--total">
            <span className="execution-attempts-chart__summary-wave" aria-hidden="true">
              <svg viewBox="0 0 16 16">
                <path d="M1.5 8h3l1.6-3 2.2 6 1.9-4H14.5" />
              </svg>
            </span>
            Total
            <strong>{total}</strong>
          </span>
        </div>

        <div className="execution-attempts-chart__range-shell">
          <span className="execution-attempts-chart__range-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16">
              <rect x="2.5" y="3.5" width="11" height="10" rx="2" />
              <path d="M5 2.5v2" />
              <path d="M11 2.5v2" />
              <path d="M2.5 6.2h11" />
            </svg>
          </span>
          <select value={range} onChange={(event) => setRange(event.target.value as AttemptsRange)}>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </header>

      <div className="line-chart-canvas execution-attempts-chart__canvas">
        <div className="execution-attempts-chart__legend">
          <span className="execution-attempts-chart__legend-item execution-attempts-chart__legend-item--placed"><i aria-hidden="true" />Placed</span>
          <span className="execution-attempts-chart__legend-item execution-attempts-chart__legend-item--closed"><i aria-hidden="true" />Closed</span>
        </div>

        <svg className="execution-attempts-chart__svg" viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`} preserveAspectRatio="none" role="img" aria-label="Placed and closed execution attempts over time">
          <rect className="execution-attempts-chart__plot-frame" x={PADDING_LEFT} y={PADDING_TOP} width={chartWidth} height={chartHeight} rx={14} />
          <line className="execution-attempts-chart__baseline" x1={PADDING_LEFT + 18} x2={VIEWBOX_WIDTH - PADDING_RIGHT - 18} y1={baselineY} y2={baselineY} />

          {buckets.map((bucket, index) => {
            const x = PADDING_LEFT + index * xStep + xStep / 2
            const placedHeight = bucket.placed * barScale
            const closedHeight = bucket.closed * barScale
            return (
              <g key={bucket.key}>
                {bucket.placed > 0 ? <line className="execution-attempts-chart__stem execution-attempts-chart__stem--placed" x1={x} x2={x} y1={baselineY - placedHeight} y2={baselineY} /> : null}
                {bucket.closed > 0 ? <line className="execution-attempts-chart__stem execution-attempts-chart__stem--closed" x1={x} x2={x} y1={baselineY} y2={baselineY + closedHeight} /> : null}
                {bucket.placed > 0 ? <circle className="execution-attempts-chart__dot execution-attempts-chart__dot--placed" cx={x} cy={baselineY - placedHeight} r={3.2} /> : null}
                {bucket.closed > 0 ? <circle className="execution-attempts-chart__dot execution-attempts-chart__dot--closed" cx={x} cy={baselineY + closedHeight} r={3.2} /> : null}
                <text className="execution-attempts-chart__axis-label" x={x} y={VIEWBOX_HEIGHT - 10} textAnchor="middle">{bucket.label}</text>
              </g>
            )
          })}
        </svg>
      </div>
    </section>
  )
}
