export interface HealthResponse {
  status: string
  service: string
  version: string
  timestamp_utc: string
}

export interface ArtifactStatus {
  name: string
  path: string
  exists: boolean
  readable?: boolean | null
  row_count?: number | null
  latest_timestamp?: string | null
  error?: string | null
}

export interface StageStatus {
  stage: string
  artifacts: ArtifactStatus[]
}

export interface PipelineStatusResponse {
  symbol: string
  timeframe: string
  generated_at: string
  stages: StageStatus[]
}

export type AccountCheckStatus = 'not_run' | 'ok' | 'failed'

export interface ExchangeStatusResponse {
  exchange: string
  private_api_present: boolean
  private_api_ready_flag: boolean
  private_api_configured: boolean
  testnet_enabled: boolean
  execution_enabled: boolean
  paper_trading_ready: boolean
  account_check_supported: boolean
  account_check_status: AccountCheckStatus
  account_check_message: string
  message: string
}

export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonArray
export interface JsonObject {
  [key: string]: JsonValue
}
export type JsonArray = JsonValue[]

export interface MarketLatestResponse {
  symbol: string
  timeframe: string
  source_path: string
  latest_timestamp: string | null
  candle: JsonObject
}

export interface MarketCandle {
  open_time: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
}

export interface MarketCandlesResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  candles: MarketCandle[]
}

export interface FeaturesLatestResponse {
  symbol: string
  timeframe: string
  source_path: string
  latest_timestamp: string | null
  snapshot: JsonObject
}

export interface InferenceLatestResponse {
  configured: boolean
  status: string
  message: string
  model_type?: string | null
  runtime?: string | null
  model_version?: string | null
  model_path?: string | null
  scaler_stats_path?: string | null
  input_layout?: string | null
  decision_threshold?: number | null
  prediction_class?: number | null
  probability_up?: number | null
  source_timestamp?: string | null
  predicted_for_timestamp?: string | null
  window_size?: number | null
  feature_count?: number | null
  timestamp_utc: string
}

export interface InferenceHistoryPoint {
  predicted_for_timestamp: string
  source_timestamp: string
  prediction_class: number
  probability_up: number
  decision_threshold: number
  model_version?: string | null
  inferred_at: string
}

export interface InferenceHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  predictions: InferenceHistoryPoint[]
}

export type SignalType = 'BUY' | 'SELL' | 'HOLD'

export interface SignalRecord {
  generated_at: string
  source_timestamp: string
  predicted_for_timestamp: string
  close_price?: number | null
  prediction_class: number
  probability_up: number
  signal_type: SignalType
  signal_reason: string
  model_version?: string | null
  model_path?: string | null
}

export interface SignalLatestResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  signal?: SignalRecord | null
}

export interface SignalHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  signals: SignalRecord[]
}

export type StrategyAction = 'OPEN_LONG' | 'OPEN_SHORT' | 'HOLD' | 'SKIP'
export type ConfidenceBucket =
  | 'STRONG_BULLISH'
  | 'MEDIUM_BULLISH'
  | 'WEAK_BULLISH'
  | 'NEUTRAL'
  | 'WEAK_BEARISH'
  | 'MEDIUM_BEARISH'
  | 'STRONG_BEARISH'
export type ContextLabel = 'supportive' | 'neutral' | 'adverse' | 'missing'

export interface StrategySupportingContext {
  feature_snapshot_available: boolean
  trend_aligned: boolean
  volatility_suitable: boolean
  volume_supported: boolean
  momentum_supported: boolean
  signal_persistent: boolean
  flip_noise_blocked: boolean
  has_open_long: boolean
  has_open_short: boolean
  counter_trend_signal: boolean
}

export interface StrategyDecisionRecord {
  decided_at: string
  source_timestamp: string
  predicted_for_timestamp: string
  probability_up: number
  prediction_class: number
  signal_type: SignalType
  confidence_bucket: ConfidenceBucket
  trend_context: ContextLabel
  volatility_context: ContextLabel
  volume_context: ContextLabel
  momentum_context: ContextLabel
  action: StrategyAction
  action_reason: string
  supporting_context: StrategySupportingContext
  strategy_version: string
  model_version?: string | null
}

export interface StrategyLatestResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  decision?: StrategyDecisionRecord | null
}

export interface StrategyHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  decisions: StrategyDecisionRecord[]
}

export type RiskAction =
  | 'OPEN_LONG'
  | 'OPEN_SHORT'
  | 'HOLD'
  | 'SKIP'
  | 'CLOSE_LONG'
  | 'CLOSE_SHORT'
  | 'FLIP_TO_LONG'
  | 'FLIP_TO_SHORT'

export interface RiskDecisionRecord {
  decided_at: string
  source_timestamp: string
  predicted_for_timestamp: string
  requested_action: RiskAction
  approved_action: RiskAction
  allowed: boolean
  order_notional_usdt: number
  approved_leverage: number
  conviction_score: number
  risk_budget_usdt: number
  stop_distance_pct?: number | null
  volatility_penalty_multiplier?: number | null
  stop_loss?: number | null
  take_profit?: number | null
  reason_codes: string[]
  size_reason: string
  leverage_reason: string
  signal_type: SignalType
  probability_up: number
  strategy_version: string
  risk_version: string
}

export interface RiskLatestResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  decision?: RiskDecisionRecord | null
}

export interface RiskHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  decisions: RiskDecisionRecord[]
}

export type AutomationCycleStatus = 'success' | 'failed' | 'skipped' | 'running'
export type AutomationStageStatus = 'ok' | 'failed' | 'skipped' | 'not_run'

export interface AutomationCycleRecord {
  cycle_id: string
  started_at: string
  finished_at?: string | null
  bar_timestamp: string
  status: AutomationCycleStatus
  data_refresh_status: AutomationStageStatus
  inference_status: AutomationStageStatus
  signal_status: AutomationStageStatus
  strategy_status: AutomationStageStatus
  risk_status: AutomationStageStatus
  execution_status: AutomationStageStatus
  position_management_status: AutomationStageStatus
  reconciliation_status: AutomationStageStatus
  dry_run: boolean
  execution_attempted: boolean
  execution_allowed: boolean
  execution_skipped_reason?: string | null
  position_management_exit_reason?: string | null
  position_management_close_requested: boolean
  position_management_close_executed: boolean
  reconciliation_blocked: boolean
  reconciliation_reason_codes: string[]
  signal_type?: string | null
  strategy_action?: string | null
  risk_allowed?: boolean | null
  probability_up?: number | null
  source_timestamp?: string | null
  predicted_for_timestamp?: string | null
  error_message?: string | null
}

export interface AutomationStatusResponse {
  enabled: boolean
  dry_run: boolean
  run_execution_step: boolean
  auto_execute_demo_orders: boolean
  last_processed_bar?: string | null
  active_cycle: boolean
  latest_cycle?: AutomationCycleRecord | null
  message: string
}

export interface AutomationLatestCycleResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  cycle?: AutomationCycleRecord | null
}

export interface AutomationHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  cycles: AutomationCycleRecord[]
}

export type PositionExitAction = 'CLOSE_LONG' | 'CLOSE_SHORT' | 'HOLD_POSITION' | 'SKIP_POSITION'

export interface PositionManagementDecisionRecord {
  decision_id: string
  decided_at: string
  trade_id: string
  symbol: string
  direction: PositionDirection
  position_status: TradeStatus
  current_price?: number | null
  entry_price?: number | null
  stop_loss?: number | null
  take_profit?: number | null
  holding_minutes: number
  exit_action: PositionExitAction
  exit_reason: string
  should_execute_close: boolean
  executed_close: boolean
  execution_skipped_reason?: string | null
  strategy_context_summary?: string | null
  source_timestamp?: string | null
  strategy_version?: string | null
  position_management_version: string
}

export interface PositionManagementLatestResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  decision?: PositionManagementDecisionRecord | null
}

export interface PositionManagementHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  decisions: PositionManagementDecisionRecord[]
}

export type ReconciliationStatus = 'ok' | 'warning' | 'mismatch' | 'blocked'
export type ReconciliationSource = 'startup' | 'post_cycle' | 'manual' | 'pre_execution' | 'post_execution'

export interface ReconciliationResultRecord {
  checked_at: string
  status: ReconciliationStatus
  local_open_count: number
  exchange_open_count: number
  matched: boolean
  mismatch_count: number
  reason_codes: string[]
  details: string[]
  block_new_execution: boolean
  source: ReconciliationSource
}

export interface ReconciliationLatestResponse {
  symbol: string
  timeframe: string
  available: boolean
  message: string
  result?: ReconciliationResultRecord | null
}

export interface ReconciliationHistoryResponse {
  symbol: string
  timeframe: string
  source_path: string
  count: number
  results: ReconciliationResultRecord[]
}

export type ExecutionMode = 'demo'
export type ExecutionStatusKind = 'disabled' | 'skipped' | 'rejected' | 'placed' | 'closed' | 'failed'
export type PositionDirection = 'LONG' | 'SHORT'
export type TradeStatus = 'OPEN' | 'CLOSED'

export interface ExecutionAttemptRecord {
  attempted_at: string
  execution_key: string
  signal_type: string
  source_timestamp?: string | null
  predicted_for_timestamp?: string | null
  symbol: string
  side?: string | null
  position_direction?: PositionDirection | null
  order_type: string
  order_notional_usdt: number
  leverage: number
  execution_mode: ExecutionMode
  success: boolean
  status: ExecutionStatusKind
  exchange_order_id?: string | null
  exchange_response_code?: string | null
  exchange_response_message?: string | null
  error_message?: string | null
}

export interface ExecutionStatusResponse {
  enabled: boolean
  mode: ExecutionMode
  symbol: string
  market_type: string
  order_type: string
  leverage: number
  max_open_positions: number
  open_positions_count: number
  demo_api_configured: boolean
  demo_trading_enabled: boolean
  dry_run_logging: boolean
  latest_execution?: ExecutionAttemptRecord | null
  message: string
}

export interface ExecutionHistoryResponse {
  symbol: string
  source_path: string
  count: number
  executions: ExecutionAttemptRecord[]
}

export interface TradeRecord {
  trade_id: string
  symbol: string
  direction: PositionDirection
  entry_time: string
  entry_price?: number | null
  stop_loss?: number | null
  take_profit?: number | null
  entry_order_id?: string | null
  exit_time?: string | null
  exit_price?: number | null
  exit_order_id?: string | null
  leverage: number
  quantity: number
  status: TradeStatus
  source_entry_signal: string
  source_exit_signal?: string | null
  realized_pnl?: number | null
  execution_mode: ExecutionMode
}

export interface OpenPositionsResponse {
  symbol: string
  source_path: string
  count: number
  positions: TradeRecord[]
}

export interface TradeHistoryResponse {
  symbol: string
  source_path: string
  count: number
  trades: TradeRecord[]
}

export interface ExecutionRunResponse {
  triggered_at: string
  signal_type?: string | null
  execution_key?: string | null
  message: string
  actions: ExecutionAttemptRecord[]
}

export interface AsyncState<T> {
  loading: boolean
  data: T | null
  error: string | null
}
