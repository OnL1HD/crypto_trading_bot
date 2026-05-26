import { CardFrame } from './CardFrame'
import type {
  AutomationStatusResponse,
  AsyncState,
  ExchangeStatusResponse,
  HealthResponse,
  PipelineStatusResponse,
  ReconciliationLatestResponse,
} from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface SystemStatusCardProps {
  healthState: AsyncState<HealthResponse>
  pipelineState: AsyncState<PipelineStatusResponse>
  exchangeState: AsyncState<ExchangeStatusResponse>
  automationState: AsyncState<AutomationStatusResponse>
  reconciliationState: AsyncState<ReconciliationLatestResponse>
}

interface PipelineSummary {
  totalArtifacts: number
  existingArtifacts: number
  readableArtifacts: number
  stageRows: Array<{ stage: string; available: number; total: number }>
}

function buildPipelineSummary(data: PipelineStatusResponse): PipelineSummary {
  let totalArtifacts = 0
  let existingArtifacts = 0
  let readableArtifacts = 0

  const stageRows = data.stages.map((stage) => {
    const total = stage.artifacts.length
    const available = stage.artifacts.filter((artifact) => artifact.exists).length

    totalArtifacts += total
    existingArtifacts += available
    readableArtifacts += stage.artifacts.filter(
      (artifact) => artifact.exists && artifact.readable !== false,
    ).length

    return {
      stage: stage.stage,
      available,
      total,
    }
  })

  return {
    totalArtifacts,
    existingArtifacts,
    readableArtifacts,
    stageRows,
  }
}

function boolLabel(value: boolean): string {
  return value ? 'Yes' : 'No'
}

function accountStatusClass(status: ExchangeStatusResponse['account_check_status']): string {
  if (status === 'ok') {
    return 'status-pill status-pill--ok'
  }
  if (status === 'failed') {
    return 'status-pill status-pill--danger'
  }
  return 'status-pill status-pill--muted'
}

function automationStatusClass(data: AutomationStatusResponse | null): string {
  if (!data) {
    return 'status-pill status-pill--muted'
  }
  if (!data.enabled) {
    return 'status-pill status-pill--muted'
  }
  if (data.dry_run) {
    return 'status-pill status-pill--warn'
  }
  return 'status-pill status-pill--ok'
}

function reconciliationStatusClass(data: ReconciliationLatestResponse | null): string {
  const result = data?.result
  if (!result) {
    return 'status-pill status-pill--muted'
  }
  if (result.status === 'ok') {
    return 'status-pill status-pill--ok'
  }
  if (result.status === 'blocked') {
    return 'status-pill status-pill--danger'
  }
  return 'status-pill status-pill--warn'
}

export function SystemStatusCard({ healthState, pipelineState, exchangeState, automationState, reconciliationState }: SystemStatusCardProps) {
  const healthStatusClass =
    healthState.data?.status === 'ok' ? 'status-pill status-pill--ok' : 'status-pill status-pill--warn'

  const pipelineSummary = pipelineState.data ? buildPipelineSummary(pipelineState.data) : null

  return (
    <CardFrame title="System Status" subtitle="API, pipeline, and exchange readiness">
      <div className="system-status-line">
        <span className={healthStatusClass}>
          API {healthState.loading ? 'Loading' : healthState.data?.status ?? 'Unavailable'}
        </span>
      </div>

      {healthState.error ? <p className="state-text state-text--error">{healthState.error}</p> : null}

      {pipelineState.loading ? <p className="state-text">Loading pipeline status...</p> : null}
      {!pipelineState.loading && pipelineState.error ? (
        <p className="state-text state-text--error">{pipelineState.error}</p>
      ) : null}

      {!pipelineState.loading && !pipelineState.error && pipelineSummary ? (
        <>
          <div className="inline-metrics">
            <span>
              Artifacts: <strong>{pipelineSummary.existingArtifacts}</strong> / {pipelineSummary.totalArtifacts}
            </span>
            <span>
              Readable: <strong>{pipelineSummary.readableArtifacts}</strong>
            </span>
            <span>
              Generated at: <strong>{formatUtcTimestamp(pipelineState.data?.generated_at)}</strong>
            </span>
          </div>

          <div className="stage-list">
            {pipelineSummary.stageRows.map((row) => (
              <div className="stage-row" key={row.stage}>
                <span>{row.stage}</span>
                <strong>
                  {row.available}/{row.total}
                </strong>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="card-subsection">
        <p className="card-subsection__title">Automation status</p>

        {automationState.loading ? <p className="state-text">Loading automation status...</p> : null}
        {!automationState.loading && automationState.error ? (
          <p className="state-text state-text--error">{automationState.error}</p>
        ) : null}

        {!automationState.loading && !automationState.error && automationState.data ? (
          <>
            <div className="exchange-check-row">
              <span className={automationStatusClass(automationState.data)}>
                Automation: {automationState.data.enabled ? (automationState.data.dry_run ? 'dry-run' : 'live-enabled') : 'disabled'}
              </span>
              <p className="state-note">{automationState.data.message}</p>
            </div>

            <div className="inline-metrics">
              <span>
                Active cycle <strong>{boolLabel(automationState.data.active_cycle)}</strong>
              </span>
              <span>
                Execution step <strong>{boolLabel(automationState.data.run_execution_step)}</strong>
              </span>
              <span>
                Auto demo orders <strong>{boolLabel(automationState.data.auto_execute_demo_orders)}</strong>
              </span>
              <span>
                Last bar <strong>{formatUtcTimestamp(automationState.data.last_processed_bar)}</strong>
              </span>
            </div>

            <div className="metrics-grid metrics-grid--compact execution-latest-grid">
              <div>
                <span className="metric-label">Latest cycle</span>
                <strong>{automationState.data.latest_cycle?.status ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Processed bar</span>
                <strong>{formatUtcTimestamp(automationState.data.latest_cycle?.bar_timestamp)}</strong>
              </div>
              <div>
                <span className="metric-label">Strategy action</span>
                <strong>{automationState.data.latest_cycle?.strategy_action ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Execution allowed</span>
                <strong>
                  {automationState.data.latest_cycle
                    ? automationState.data.latest_cycle.execution_allowed
                      ? 'Yes'
                      : 'No'
                    : '--'}
                </strong>
              </div>
              <div>
                <span className="metric-label">Execution skip reason</span>
                <strong>{automationState.data.latest_cycle?.execution_skipped_reason ?? '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Cycle error</span>
                <strong>{automationState.data.latest_cycle?.error_message ?? '--'}</strong>
              </div>
            </div>
          </>
        ) : null}
      </div>

      <div className="card-subsection">
        <p className="card-subsection__title">Reconciliation</p>

        {reconciliationState.loading ? <p className="state-text">Loading reconciliation status...</p> : null}
        {!reconciliationState.loading && reconciliationState.error ? (
          <p className="state-text state-text--error">{reconciliationState.error}</p>
        ) : null}

        {!reconciliationState.loading && !reconciliationState.error && reconciliationState.data ? (
          <>
            <div className="exchange-check-row">
              <span className={reconciliationStatusClass(reconciliationState.data)}>
                Reconciliation: {reconciliationState.data.result?.status ?? 'unavailable'}
              </span>
              <p className="state-note">{reconciliationState.data.message}</p>
            </div>

            <div className="inline-metrics">
              <span>
                Matched <strong>{reconciliationState.data.result ? boolLabel(reconciliationState.data.result.matched) : '--'}</strong>
              </span>
              <span>
                Local open <strong>{reconciliationState.data.result?.local_open_count ?? '--'}</strong>
              </span>
              <span>
                Exchange open <strong>{reconciliationState.data.result?.exchange_open_count ?? '--'}</strong>
              </span>
              <span>
                Blocks automation <strong>{reconciliationState.data.result ? boolLabel(reconciliationState.data.result.block_new_execution) : '--'}</strong>
              </span>
            </div>

            <div className="metrics-grid metrics-grid--compact execution-latest-grid">
              <div>
                <span className="metric-label">Reason codes</span>
                <strong>{reconciliationState.data.result?.reason_codes.join(', ') || '--'}</strong>
              </div>
              <div>
                <span className="metric-label">Checked at</span>
                <strong>{formatUtcTimestamp(reconciliationState.data.result?.checked_at)}</strong>
              </div>
            </div>
          </>
        ) : null}
      </div>

      <div className="card-subsection">
        <p className="card-subsection__title">Exchange readiness</p>

        {exchangeState.loading ? <p className="state-text">Loading exchange status...</p> : null}
        {!exchangeState.loading && exchangeState.error ? (
          <p className="state-text state-text--error">{exchangeState.error}</p>
        ) : null}

        {!exchangeState.loading && !exchangeState.error && exchangeState.data ? (
          <>
            <div className="inline-metrics">
              <span>
                Exchange: <strong>{exchangeState.data.exchange}</strong>
              </span>
              <span>
                Configured: <strong>{boolLabel(exchangeState.data.private_api_configured)}</strong>
              </span>
              <span>
                Testnet: <strong>{exchangeState.data.testnet_enabled ? 'On' : 'Off'}</strong>
              </span>
              <span>
                Execution: <strong>{exchangeState.data.execution_enabled ? 'Enabled' : 'Disabled'}</strong>
              </span>
              <span>
                Paper ready: <strong>{boolLabel(exchangeState.data.paper_trading_ready)}</strong>
              </span>
            </div>

            <div className="exchange-check-row">
              <span className={accountStatusClass(exchangeState.data.account_check_status)}>
                Account check: {exchangeState.data.account_check_status}
              </span>
              <p className="state-note">{exchangeState.data.account_check_message}</p>
              <p className="state-note">{exchangeState.data.message}</p>
            </div>
          </>
        ) : null}
      </div>
    </CardFrame>
  )
}
