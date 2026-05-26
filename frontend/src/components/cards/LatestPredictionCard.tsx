import type { ReactNode } from 'react'
import { CardFrame } from './CardFrame'
import type {
  AsyncState,
  InferenceLatestResponse,
  SignalLatestResponse,
  StrategyLatestResponse,
} from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface LatestPredictionCardProps {
  inferenceState: AsyncState<InferenceLatestResponse>
  signalState: AsyncState<SignalLatestResponse>
  strategyState: AsyncState<StrategyLatestResponse>
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

function classLabel(predictionClass: number | null | undefined): string {
  if (predictionClass === 1) {
    return 'UP'
  }
  if (predictionClass === 0) {
    return 'DOWN'
  }
  return 'N/A'
}

function formatProbability(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--'
  }

  return `${(value * 100).toFixed(2)}%`
}

function predictionLabel(predictionClass: number | null | undefined): string {
  if (predictionClass === 1) {
    return 'Model prediction'
  }
  if (predictionClass === 0) {
    return 'Model prediction'
  }
  return 'Model prediction'
}

function probabilityLabel(predictionClass: number | null | undefined): string {
  if (predictionClass === 1) {
    return 'Probability (Up)'
  }
  if (predictionClass === 0) {
    return 'Probability (Down)'
  }
  return 'Probability'
}

function predictionProbability(
  predictionClass: number | null | undefined,
  probabilityUp: number | null | undefined,
): string {
  if (typeof probabilityUp !== 'number' || !Number.isFinite(probabilityUp)) {
    return '--'
  }

  if (predictionClass === 0) {
    return formatProbability(1 - probabilityUp)
  }

  return formatProbability(probabilityUp)
}

function signalLabel(value: string | undefined): string {
  if (value === 'BUY' || value === 'SELL' || value === 'HOLD') {
    return value
  }
  return '--'
}

function contextToneLabel(value: string | undefined): string {
  if (value === 'supportive') {
    return 'Supportive'
  }
  if (value === 'neutral') {
    return 'Neutral'
  }
  if (value === 'adverse') {
    return 'Adverse'
  }
  if (value === 'missing') {
    return 'Missing'
  }
  return '--'
}

function contextSummary(latestStrategy: StrategyLatestResponse['decision']): string {
  if (!latestStrategy) {
    return '--'
  }

  return [
    `Trend ${contextToneLabel(latestStrategy.trend_context)}`,
    `Volatility ${contextToneLabel(latestStrategy.volatility_context)}`,
    `Volume ${contextToneLabel(latestStrategy.volume_context)}`,
    `Momentum ${contextToneLabel(latestStrategy.momentum_context)}`,
  ].join(' • ')
}

function strategyReasonLabel(value: string | undefined): string {
  if (!value) {
    return '--'
  }

  const labels: Record<string, string> = {
    base_signal_hold: 'Base signal is neutral, so the strategy holds.',
    strategy_hold_no_tradeable_signal: 'No tradeable setup is present, so the strategy holds.',
    long_position_already_open: 'A long position is already open, so no new long is taken.',
    short_position_already_open: 'A short position is already open, so no new short is taken.',
    opposite_short_position_open: 'A short position is already open, so a new long is skipped.',
    opposite_long_position_open: 'A long position is already open, so a new short is skipped.',
    buy_signal_below_entry_threshold: 'Bullish signal is not strong enough for a long entry.',
    sell_signal_below_entry_threshold: 'Bearish signal is not strong enough for a short entry.',
    flip_noise_guard_blocked: 'Possible one-bar reversal noise was filtered out.',
    signal_not_persistent: 'The signal has not stayed consistent long enough yet.',
    counter_trend_signal_blocked: 'The setup goes against the trend and was filtered out.',
    trend_alignment_required: 'The setup needs stronger trend alignment before entry.',
    volatility_filter_blocked: 'Volatility conditions are not suitable for entry.',
    volume_filter_blocked: 'Volume confirmation is too weak for entry.',
    momentum_filter_blocked: 'Momentum does not support this setup.',
    strong_counter_trend_signal_allowed: 'Strong counter-trend signal is allowed by strategy settings.',
    long_entry_approved: 'Long entry conditions are satisfied.',
    short_entry_approved: 'Short entry conditions are satisfied.',
    long_entry_approved_strong_confidence: 'Long entry is approved with strong confidence.',
    short_entry_approved_strong_confidence: 'Short entry is approved with strong confidence.',
    long_entry_approved_context_confirmed: 'Long entry is approved with supporting context.',
    short_entry_approved_context_confirmed: 'Short entry is approved with supporting context.',
  }

  return labels[value] ?? value.replaceAll('_', ' ')
}

export function LatestPredictionCard({ inferenceState, signalState, strategyState }: LatestPredictionCardProps) {
  const inferenceData = inferenceState.data
  const latestSignal = signalState.data?.signal
  const latestStrategy = strategyState.data?.decision

  return (
    <CardFrame
      title="Latest Prediction"
      subtitle="Most recent inference output from the model"
      className="card-frame--model"
      statusSlot={<LiveBadge />}
    >
      {inferenceState.loading ? <p className="state-text">Loading latest inference...</p> : null}
      {!inferenceState.loading && inferenceState.error ? (
        <p className="state-text state-text--error">{inferenceState.error}</p>
      ) : null}

      {!inferenceState.loading && !inferenceState.error && inferenceData ? (
        <>
          {!inferenceData.configured ? (
            <div className="placeholder-state">
              <span className="status-pill status-pill--muted">{inferenceData.status}</span>
              <p>{inferenceData.message}</p>
              <p className="state-note">
                Endpoint is wired for real model inference when artifacts are ready.
              </p>
            </div>
          ) : (
            <div className="metrics-grid metrics-grid--compact metrics-grid--model">
              <MetricTile
                label={predictionLabel(inferenceData.prediction_class)}
                value={classLabel(inferenceData.prediction_class)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M1.75 8h2.2l1.25-2.7L7.5 11l1.9-6 1.35 3H14.25" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
              />
              <MetricTile
                label={probabilityLabel(inferenceData.prediction_class)}
                value={predictionProbability(inferenceData.prediction_class, inferenceData.probability_up)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                    <circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.25" />
                  </svg>
                }
              />
              <MetricTile
                label="Inference time"
                value={formatUtcTimestamp(inferenceData.timestamp_utc)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                    <path d="M8 4.8v3.5l2.2 1.3" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
              />
              <MetricTile
                label="System signal"
                value={signalLabel(latestSignal?.signal_type)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
                    <path d="M5.1 8h5.8M8 5.1 10.9 8 8 10.9" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
              />
              <MetricTile
                label="Signal for"
                value={formatUtcTimestamp(latestSignal?.predicted_for_timestamp)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <rect x="2.5" y="3.5" width="11" height="10" rx="2" stroke="currentColor" strokeWidth="1.25" />
                    <path d="M5.1 2.5v2M10.9 2.5v2M2.5 6.2h11" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
                  </svg>
                }
              />
              <MetricTile
                label="Strategy action"
                value={latestStrategy?.action ?? '--'}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M4 4.4h6.7M8.2 2.5l2.5 1.9-2.5 1.8M12 11.6H5.3M7.8 9.8 5.3 11.6l2.5 1.9" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
              />
              <MetricTile
                label="Confidence bucket"
                value={latestStrategy?.confidence_bucket ?? '--'}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M8 2.2 12.3 4v3.2c0 2.7-1.8 5.1-4.3 6.1-2.5-1-4.3-3.4-4.3-6.1V4L8 2.2Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
                    <path d="m6.4 7.9 1 1 2-2.1" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                }
              />
              <MetricTile
                label="Strategy reason"
                value={strategyReasonLabel(latestStrategy?.action_reason)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M4.3 3.4h5.2l2.2 2.2v7H4.3z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
                    <path d="M9.5 3.4v2.2h2.2M5.5 8h4.8M5.5 10.5h3.5" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
                  </svg>
                }
              />
              <MetricTile
                label="Context summary"
                value={contextSummary(latestStrategy)}
                icon={
                  <svg viewBox="0 0 16 16" fill="none">
                    <circle cx="4" cy="4" r="1.4" fill="currentColor" />
                    <circle cx="12" cy="4" r="1.4" fill="currentColor" />
                    <circle cx="8" cy="12" r="1.4" fill="currentColor" />
                    <path d="M5.2 4h5.6M4.8 5l2.4 5.3M11.2 5 8.8 10.3" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
                  </svg>
                }
              />
            </div>
          )}

          {!signalState.loading && signalState.error ? (
            <p className="state-note state-text--error">Signal load error: {signalState.error}</p>
          ) : null}
          {!strategyState.loading && strategyState.error ? (
            <p className="state-note state-text--error">Strategy load error: {strategyState.error}</p>
          ) : null}
        </>
      ) : null}
    </CardFrame>
  )
}
