import type {
  AsyncState,
  ExecutionStatusResponse,
  OpenPositionsResponse,
  PositionManagementLatestResponse,
} from '../../types/api'
import { formatUtcTimestamp } from '../../utils/time'

interface ExecutionCoreSectionProps {
  executionState: AsyncState<ExecutionStatusResponse>
  openPositionsState: AsyncState<OpenPositionsResponse>
  positionManagementState: AsyncState<PositionManagementLatestResponse>
}

type StatusTone = 'ok' | 'warn' | 'danger' | 'muted'

interface StatusPresentation {
  eyebrow: string
  headline: string
  gate: string
  summary: string
  tone: StatusTone
}

interface InfoNodeProps {
  title: string
  value: string
  className: string
  icon?: 'pulse' | 'calendar' | 'document' | 'trend' | 'shield' | 'flag' | 'clock' | 'dollar' | 'target' | 'check'
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

function yesNo(value: boolean | null | undefined): string {
  if (typeof value !== 'boolean') {
    return '--'
  }

  return value ? 'Yes' : 'No'
}

function titleCase(text: string | null | undefined): string {
  if (!text) {
    return '--'
  }

  return text
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function displayLeverage(execution: ExecutionStatusResponse | null, positions: OpenPositionsResponse['positions'] | undefined): string {
  const openPositionLeverage = positions && positions.length > 0 ? positions[0]?.leverage : null
  const latestExecutionLeverage = execution?.latest_execution?.leverage
  const leverage = openPositionLeverage ?? latestExecutionLeverage

  if (typeof leverage !== 'number' || !Number.isFinite(leverage)) {
    return '--'
  }

  return `${leverage}x`
}

function getStatusPresentation(data: ExecutionStatusResponse): StatusPresentation {
  if (!data.enabled) {
    return {
      eyebrow: 'Execution offline',
      headline: 'Execution Disabled',
      gate: 'Disabled in config',
      summary: 'The execution layer is switched off in config, so no new orders can be sent.',
      tone: 'muted',
    }
  }

  if (!data.demo_api_configured) {
    return {
      eyebrow: 'Setup required',
      headline: 'Credentials Missing',
      gate: 'Missing demo credentials',
      summary: 'Execution is enabled, but demo API credentials are not available to the backend.',
      tone: 'danger',
    }
  }

  if (!data.demo_trading_enabled) {
    return {
      eyebrow: 'Config blocked',
      headline: 'Demo Trading Off',
      gate: 'Demo trading flag off',
      summary: 'The execution service is configured, but demo trading is not enabled for order placement.',
      tone: 'warn',
    }
  }

  if (data.open_positions_count > 0) {
    return {
      eyebrow: 'Live management',
      headline: 'Managing Open Position',
      gate: 'Position management active',
      summary: 'Execution is active and currently tracking at least one open demo position.',
      tone: 'ok',
    }
  }

  return {
    eyebrow: 'Ready',
    headline: 'Ready to Execute',
    gate: 'Ready',
    summary: 'All systems are aligned. Parameters verified. Execution is ready.',
    tone: 'ok',
  }
}

function latestActionLabel(data: ExecutionStatusResponse | null): string {
  const latest = data?.latest_execution
  if (!latest) {
    return 'No recent activity'
  }

  const signalLabel = titleCase(latest.signal_type)
  const statusLabel = titleCase(latest.status)
  return signalLabel === '--' ? statusLabel : `${signalLabel} - ${statusLabel}`
}

function latestDetailLabel(data: ExecutionStatusResponse | null): string {
  const latest = data?.latest_execution
  if (!latest) {
    return 'Awaiting first result'
  }

  if (latest.error_message) {
    return latest.error_message
  }

  if (latest.exchange_response_message) {
    return latest.exchange_response_message
  }

  return 'OK'
}

function InfoNode({ title, value, className, icon }: InfoNodeProps) {
  return (
    <article className={`execution-core-node ${className}`}>
      {icon ? (
        <div className={`execution-core-node__icon execution-core-node__icon--${icon}`} aria-hidden="true">
          <svg viewBox="0 0 24 24" className="execution-core-node__icon-svg">
            {icon === 'pulse' ? (
              <path d="M2 12h4l2.2-4.5L12 17l2.1-4H22" />
            ) : icon === 'document' ? (
              <>
                <path d="M8 3.5h6l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 7 20V5a1.5 1.5 0 0 1 1-1.5Z" />
                <path d="M14 3.5V8h4" />
                <path d="M10 12h6" />
                <path d="M10 15.5h6" />
              </>
            ) : icon === 'trend' ? (
              <>
                <path d="M5 16.5 10.2 11.3l3.4 3.4L19 9.3" />
                <path d="M14.8 9.3H19v4.2" />
              </>
            ) : icon === 'shield' ? (
              <>
                <path d="M12 3.5 18.5 6v5.6c0 4.2-2.7 7.4-6.5 8.9-3.8-1.5-6.5-4.7-6.5-8.9V6L12 3.5Z" />
                <path d="M9.2 12.1 11.2 14.1 14.9 10.4" />
              </>
            ) : icon === 'flag' ? (
              <>
                <path d="M7 4v16" />
                <path d="M8 5.5h8.5l-1.8 3.3 1.8 3.2H8Z" />
              </>
            ) : icon === 'clock' ? (
              <>
                <circle cx="12" cy="12" r="8" />
                <path d="M12 8v4.4l3 1.8" />
              </>
            ) : icon === 'dollar' ? (
              <>
                <path d="M12 4v16" />
                <path d="M15.8 7.2c-.6-.9-1.9-1.5-3.5-1.5-2.1 0-3.8 1.1-3.8 2.8 0 1.7 1.3 2.3 3.8 2.9 2.2.6 3.8 1.1 3.8 3 0 1.8-1.7 3-4 3-1.8 0-3.4-.7-4.1-1.8" />
              </>
            ) : icon === 'target' ? (
              <>
                <circle cx="12" cy="12" r="7.6" />
                <circle cx="12" cy="12" r="3.2" />
                <path d="M12 2.8v3.1" />
                <path d="M12 18.1v3.1" />
                <path d="M2.8 12h3.1" />
                <path d="M18.1 12h3.1" />
              </>
            ) : icon === 'check' ? (
              <>
                <circle cx="12" cy="12" r="8" />
                <path d="M8.7 12.2 11 14.5 15.6 9.9" />
              </>
            ) : (
              <>
                <rect x="4" y="6" width="16" height="14" rx="3" />
                <path d="M8 4v4" />
                <path d="M16 4v4" />
                <path d="M4 10h16" />
              </>
            )}
          </svg>
        </div>
      ) : null}
      <div className="execution-core-node__copy">
        <span className="execution-core-node__label">{title}</span>
        <strong className="execution-core-node__value">{value}</strong>
      </div>
    </article>
  )
}

export function ExecutionCoreSection({
  executionState,
  openPositionsState,
  positionManagementState,
}: ExecutionCoreSectionProps) {
  const execution = executionState.data
  const positions = openPositionsState.data?.positions ?? []
  const lifecycleDecision = positionManagementState.data?.decision ?? null
  const status = execution ? getStatusPresentation(execution) : null

  return (
    <section className="execution-core-section" aria-label="Execution overview section">
      <svg
        className="execution-core-network"
        viewBox="0 0 1600 940"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="executionConnectorStroke" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(112, 98, 255, 0.02)" />
            <stop offset="38%" stopColor="rgba(125, 109, 255, 0.55)" />
            <stop offset="68%" stopColor="rgba(153, 140, 255, 0.88)" />
            <stop offset="100%" stopColor="rgba(176, 230, 255, 0.95)" />
          </linearGradient>
          <filter id="executionConnectorGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g className="execution-core-network__group execution-core-network__group--left">
          <path d="M800 506 C 728 506, 642 430, 546 398 S 326 378, 276 378" />
          <path d="M800 494 C 720 486, 628 354, 472 298 S 300 282, 246 282" />
          <path d="M800 474 C 716 456, 624 250, 460 192 S 360 160, 314 160" />
          <path d="M734 520 C 654 538, 556 586, 372 604 S 154 608, 92 608" />
          <path d="M778 624 C 706 638, 646 730, 582 766 S 438 786, 356 786" />
          <path d="M800 660 C 800 700, 754 730, 700 776 S 652 840, 646 860" />
        </g>

        <g className="execution-core-network__group execution-core-network__group--right">
          <path d="M800 506 C 874 506, 958 430, 1056 398 S 1278 384, 1328 384" />
          <path d="M800 494 C 880 486, 972 354, 1128 298 S 1296 282, 1348 282" />
          <path d="M800 474 C 884 456, 976 250, 1140 194 S 1240 164, 1288 164" />
          <path d="M866 520 C 946 538, 1044 590, 1228 620 S 1440 632, 1512 632" />
          <path d="M778 624 C 850 638, 910 730, 974 766 S 1118 786, 1200 786" />
          <path d="M822 660 C 822 700, 866 730, 920 776 S 968 840, 974 860" />
        </g>

        <g className="execution-core-network__anchor-group">
          <circle cx="92" cy="608" r="3.2" />
          <circle cx="356" cy="786" r="3.2" />
          <circle cx="646" cy="860" r="3.2" />
          <circle cx="1512" cy="632" r="3.2" />
          <circle cx="1200" cy="786" r="3.2" />
          <circle cx="974" cy="860" r="3.2" />
          <circle cx="800" cy="506" r="4.4" />
          <circle cx="800" cy="474" r="3.6" />
          <circle cx="800" cy="660" r="3.6" />
        </g>
      </svg>

      <article className="execution-core-panel execution-core-panel--status">
        <p className="execution-core-panel__eyebrow">Execution Status</p>
        {executionState.loading ? <p className="state-text">Loading execution status...</p> : null}
        {!executionState.loading && executionState.error ? (
          <p className="state-text state-text--error">{executionState.error}</p>
        ) : null}
        {!executionState.loading && !executionState.error && execution && status ? (
          <>
            <div className="execution-core-panel__status-row">
              <span className={`status-pill status-pill--${status.tone}`}>{status.eyebrow}</span>
              <strong className="execution-core-panel__headline">{status.headline}</strong>
            </div>
            <p className="execution-core-panel__copy">{status.summary}</p>
          </>
        ) : null}
      </article>

      <InfoNode title="Last action" value={latestActionLabel(execution)} className="execution-core-node--action" icon="pulse" />
      <InfoNode title="Latest detail" value={latestDetailLabel(execution)} className="execution-core-node--detail" icon="document" />
      <InfoNode title="Leverage" value={displayLeverage(execution, positions)} className="execution-core-node--leverage" icon="trend" />
      <InfoNode
        title="Last updated"
        value={formatUtcTimestamp(execution?.latest_execution?.attempted_at)}
        className="execution-core-node--updated"
        icon="calendar"
      />
      <InfoNode
        title="Open positions"
        value={execution ? `${execution.open_positions_count} / ${execution.max_open_positions}` : '--'}
        className="execution-core-node--count"
        icon="trend"
      />
      <InfoNode title="Current gate" value={status?.gate ?? '--'} className="execution-core-node--gate" icon="shield" />

      <article className="execution-core-panel execution-core-panel--lifecycle">
        <p className="execution-core-panel__eyebrow">Position Lifecycle</p>
        {positionManagementState.loading ? <p className="state-text">Loading lifecycle decision...</p> : null}
        {!positionManagementState.loading && positionManagementState.error ? (
          <p className="state-text state-text--error">{positionManagementState.error}</p>
        ) : null}
        {!positionManagementState.loading && !positionManagementState.error ? (
          lifecycleDecision ? (
            <div className="execution-core-definition-list">
              <div><span>Trade</span><strong>{lifecycleDecision.trade_id.slice(0, 10)}</strong></div>
              <div><span>Action</span><strong>{titleCase(lifecycleDecision.exit_action)}</strong></div>
              <div><span>Reason</span><strong>{lifecycleDecision.exit_reason}</strong></div>
              <div><span>Holding minutes</span><strong>{formatNumber(lifecycleDecision.holding_minutes, 1)}</strong></div>
              <div><span>Current price</span><strong>{formatNumber(lifecycleDecision.current_price, 2)}</strong></div>
              <div><span>Stop / TP</span><strong>{`${formatNumber(lifecycleDecision.stop_loss, 2)} / ${formatNumber(lifecycleDecision.take_profit, 2)}`}</strong></div>
              <div><span>Would close</span><strong>{yesNo(lifecycleDecision.should_execute_close)}</strong></div>
              <div><span>Executed close</span><strong>{yesNo(lifecycleDecision.executed_close)}</strong></div>
              <div><span>Skip reason</span><strong>{lifecycleDecision.execution_skipped_reason ?? '--'}</strong></div>
            </div>
          ) : (
            <div className="placeholder-state execution-core-placeholder">
              <span className="status-pill status-pill--muted">No lifecycle decisions</span>
              <p>No open positions have been evaluated yet.</p>
            </div>
          )
        ) : null}
      </article>

      <article className="execution-core-panel execution-core-panel--positions">
        <p className="execution-core-panel__eyebrow">Open Positions</p>
        {openPositionsState.loading ? <p className="state-text">Loading open positions...</p> : null}
        {!openPositionsState.loading && openPositionsState.error ? (
          <p className="state-text state-text--error">{openPositionsState.error}</p>
        ) : null}
        {!openPositionsState.loading && !openPositionsState.error ? (
          positions.length > 0 ? (
            <div className="execution-core-positions-list">
              {positions.slice(0, 2).map((position) => (
                <article className="execution-core-positions-item" key={position.trade_id}>
                  <div>
                    <span>{position.direction}</span>
                    <strong>{position.symbol}</strong>
                  </div>
                  <div>
                    <span>Qty</span>
                    <strong>{formatNumber(position.quantity, 5)}</strong>
                  </div>
                  <div>
                    <span>Leverage</span>
                    <strong>{formatNumber(position.leverage, 0)}x</strong>
                  </div>
                  <div>
                    <span>Entry</span>
                    <strong>{formatNumber(position.entry_price, 2)}</strong>
                  </div>
                  <div>
                    <span>Stop / TP</span>
                    <strong>{`${formatNumber(position.stop_loss, 2)} / ${formatNumber(position.take_profit, 2)}`}</strong>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="execution-core-empty-state">
              <div className="execution-core-empty-state__entity" aria-hidden="true">
                <div className="execution-core-empty-state__entity-head" />
                <div className="execution-core-empty-state__entity-body" />
                <span className="execution-core-empty-state__entity-spark execution-core-empty-state__entity-spark--left" />
                <span className="execution-core-empty-state__entity-spark execution-core-empty-state__entity-spark--right" />
              </div>
              <strong>No open positions</strong>
              <p>The system has not recorded any open demo trades yet.</p>
            </div>
          )
        ) : null}
      </article>

      <InfoNode title="Reason" value={lifecycleDecision?.exit_reason ?? '--'} className="execution-core-node--reason" icon="flag" />
      <InfoNode
        title="Holding minutes"
        value={formatNumber(lifecycleDecision?.holding_minutes, 1)}
        className="execution-core-node--holding"
        icon="clock"
      />
      <InfoNode
        title="Current price"
        value={formatNumber(lifecycleDecision?.current_price, 2)}
        className="execution-core-node--price"
        icon="dollar"
      />
      <InfoNode
        title="Stop / TP"
        value={`${formatNumber(lifecycleDecision?.stop_loss, 2)} / ${formatNumber(lifecycleDecision?.take_profit, 2)}`}
        className="execution-core-node--stop"
        icon="target"
      />
      <InfoNode title="Would close" value={yesNo(lifecycleDecision?.should_execute_close)} className="execution-core-node--would-close" icon="check" />
      <InfoNode title="Executed close" value={yesNo(lifecycleDecision?.executed_close)} className="execution-core-node--executed-close" icon="check" />
    </section>
  )
}
