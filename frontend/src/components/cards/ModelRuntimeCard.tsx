import { CardFrame } from './CardFrame'
import type { AsyncState, InferenceLatestResponse } from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface ModelRuntimeCardProps {
  inferenceState: AsyncState<InferenceLatestResponse>
}

export function ModelRuntimeCard({ inferenceState }: ModelRuntimeCardProps) {
  const inferenceData = inferenceState.data

  return (
    <CardFrame title="Model Runtime" subtitle="Current model configuration and inference metadata">
      {inferenceState.loading ? <p className="state-text">Loading runtime metadata...</p> : null}
      {!inferenceState.loading && inferenceState.error ? (
        <p className="state-text state-text--error">{inferenceState.error}</p>
      ) : null}

      {!inferenceState.loading && !inferenceState.error ? (
        inferenceData ? (
          !inferenceData.configured ? (
            <div className="placeholder-state">
              <span className="status-pill status-pill--muted">{inferenceData.status}</span>
              <p>{inferenceData.message}</p>
            </div>
          ) : (
            <div className="metrics-grid metrics-grid--compact">
              <div>
                <span className="metric-label">Model version</span>
                <strong>{inferenceData.model_version ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Model type</span>
                <strong>{inferenceData.model_type ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Threshold</span>
                <strong>
                  {typeof inferenceData.decision_threshold === 'number'
                    ? inferenceData.decision_threshold.toFixed(2)
                    : '--'}
                </strong>
              </div>
              <div>
                <span className="metric-label">Status</span>
                <strong>{inferenceData.status}</strong>
              </div>
              <div>
                <span className="metric-label">Window size</span>
                <strong>{inferenceData.window_size ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Feature count</span>
                <strong>{inferenceData.feature_count ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Inference time</span>
                <strong>{formatUtcTimestamp(inferenceData.timestamp_utc)}</strong>
              </div>
              <div>
                <span className="metric-label">Source time</span>
                <strong>{formatUtcTimestamp(inferenceData.source_timestamp)}</strong>
              </div>
            </div>
          )
        ) : null
      ) : null}
    </CardFrame>
  )
}
