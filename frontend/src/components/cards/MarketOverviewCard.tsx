import { CardFrame } from './CardFrame'
import type { AsyncState, FeaturesLatestResponse, JsonValue, MarketLatestResponse } from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface MarketOverviewCardProps {
  marketState: AsyncState<MarketLatestResponse>
  featuresState: AsyncState<FeaturesLatestResponse>
}

function numberFromJson(value: JsonValue | undefined): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function formatNumber(value: number | null, digits = 2): string {
  if (value === null) {
    return '--'
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatCompact(value: number | null): string {
  if (value === null) {
    return '--'
  }

  return value.toLocaleString(undefined, {
    notation: 'compact',
    maximumFractionDigits: 2,
  })
}

type MarketMetricTone = 'open' | 'high' | 'low' | 'close' | 'volume' | 'time' | 'rsi' | 'macd' | 'atr'

interface MetricTileProps {
  label: string
  value: string
  tone: MarketMetricTone
  compactValue?: boolean
  variant?: 'default' | 'feature'
}

function MetricIcon({ tone }: { tone: MarketMetricTone }) {
  if (tone === 'high') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2.5 10.5 6 7l2.3 2.3L13.5 4" />
        <path d="M10.5 4h3v3" />
      </svg>
    )
  }

  if (tone === 'low') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2.5 5.5 6 9l2.3-2.3L13.5 12" />
        <path d="M10.5 12h3V9" />
      </svg>
    )
  }

  if (tone === 'close') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="8" cy="8" r="5" />
        <circle cx="8" cy="8" r="1.5" />
      </svg>
    )
  }

  if (tone === 'volume') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M3 12.5V8.5" />
        <path d="M7 12.5V5.5" />
        <path d="M11 12.5V9.5" />
        <path d="M13.5 12.5H2.5" />
      </svg>
    )
  }

  if (tone === 'time') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="8" cy="8" r="5" />
        <path d="M8 5.2v3.2l2.2 1.3" />
      </svg>
    )
  }

  if (tone === 'rsi') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2.5 10.5 5 8l2.2 2.2L10 5.5l3.5 3.5" />
        <path d="M2.5 12.5h11" />
      </svg>
    )
  }

  if (tone === 'macd') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2.5 8c1.3-2.9 2.7-2.9 4 0s2.7 2.9 4 0 2.7-2.9 3.5 0" />
      </svg>
    )
  }

  if (tone === 'atr') {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M3 11 5.4 8.2l1.9 1.9L10.8 5l2.2 2.6" />
        <path d="M3 5.2V11h10" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2.5 10.5 5.5 7.5l2.1 2.1L10.5 4.5" />
      <path d="M2.5 12.5h11" />
      <path d="M10 4.5h2.5V7" />
    </svg>
  )
}

function MetricTile({ label, value, tone, compactValue = false, variant = 'default' }: MetricTileProps) {
  return (
    <article className={`market-overview-card__metric market-overview-card__metric--${tone} ${variant === 'feature' ? 'market-overview-card__metric--feature' : ''}`}>
      <div className="market-overview-card__metric-label">
        <span className="market-overview-card__metric-icon">
          <MetricIcon tone={tone} />
        </span>
        <span>{label}</span>
      </div>
      <strong className={compactValue ? 'market-overview-card__metric-value market-overview-card__metric-value--compact' : 'market-overview-card__metric-value'}>
        {value}
      </strong>
    </article>
  )
}

export function MarketOverviewCard({ marketState, featuresState }: MarketOverviewCardProps) {
  const subtitle = marketState.data
    ? `${marketState.data.symbol} • ${marketState.data.timeframe}`
    : 'Latest processed market candle'

  return (
    <CardFrame
      title="Market Overview"
      subtitle={subtitle}
      className="market-overview-card"
      statusSlot={(
        <div className="market-overview-card__live-pill">
          <span className="market-overview-card__live-pill-dot" aria-hidden="true" />
          <span>Live snapshot</span>
        </div>
      )}
    >
      {marketState.loading ? <p className="state-text">Loading latest market data...</p> : null}
      {!marketState.loading && marketState.error ? (
        <p className="state-text state-text--error">{marketState.error}</p>
      ) : null}

      {!marketState.loading && !marketState.error && marketState.data ? (
        <>
          <div className="market-overview-card__content-row">
            <section className="market-overview-card__panel market-overview-card__panel--snapshot" aria-label="Market snapshot">
              <div className="market-overview-card__panel-header">
                <p className="market-overview-card__section-title">Market snapshot</p>
                <div className="market-overview-card__panel-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </div>

              <div className="market-overview-card__metrics-grid">
                <MetricTile label="Open" value={formatNumber(numberFromJson(marketState.data.candle.open), 2)} tone="open" />
                <MetricTile label="High" value={formatNumber(numberFromJson(marketState.data.candle.high), 2)} tone="high" />
                <MetricTile label="Low" value={formatNumber(numberFromJson(marketState.data.candle.low), 2)} tone="low" />
                <MetricTile label="Close" value={formatNumber(numberFromJson(marketState.data.candle.close), 2)} tone="close" />
                <MetricTile label="Volume" value={formatCompact(numberFromJson(marketState.data.candle.volume))} tone="volume" />
                <MetricTile label="Latest Candle" value={formatUtcTimestamp(marketState.data.latest_timestamp)} tone="time" compactValue />
              </div>
            </section>

            <section className="market-overview-card__panel market-overview-card__panel--features" aria-label="Feature pulse">
              <div className="market-overview-card__panel-header market-overview-card__panel-header--features">
                <div className="market-overview-card__feature-heading">
                  <span className="market-overview-card__feature-orb" aria-hidden="true">
                    <MetricIcon tone="macd" />
                  </span>
                  <p className="market-overview-card__section-title">Feature pulse</p>
                </div>

                <div className="market-overview-card__panel-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </div>

              {featuresState.loading ? <p className="state-text">Loading latest feature snapshot...</p> : null}
              {!featuresState.loading && featuresState.error ? (
                <p className="state-text state-text--error">{featuresState.error}</p>
              ) : null}

              {!featuresState.loading && !featuresState.error && featuresState.data ? (
                <div className="market-overview-card__metrics-grid market-overview-card__metrics-grid--features">
                  <MetricTile label="RSI14" value={formatNumber(numberFromJson(featuresState.data.snapshot.rsi_14), 2)} tone="rsi" variant="feature" />
                  <MetricTile label="MACD hist" value={formatNumber(numberFromJson(featuresState.data.snapshot.macd_hist), 3)} tone="macd" variant="feature" />
                  <MetricTile label="ATR%" value={formatNumber(numberFromJson(featuresState.data.snapshot.atr_14_pct), 4)} tone="atr" variant="feature" />
                </div>
              ) : null}
            </section>
          </div>
        </>
      ) : null}
    </CardFrame>
  )
}
