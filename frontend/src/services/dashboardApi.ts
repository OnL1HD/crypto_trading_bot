import { apiGet, apiPost } from './apiClient'
import type {
  AutomationHistoryResponse,
  AutomationLatestCycleResponse,
  AutomationStatusResponse,
  ExecutionHistoryResponse,
  ExecutionRunResponse,
  ExecutionStatusResponse,
  ExchangeStatusResponse,
  InferenceHistoryResponse,
  FeaturesLatestResponse,
  HealthResponse,
  InferenceLatestResponse,
  MarketCandlesResponse,
  MarketLatestResponse,
  OpenPositionsResponse,
  PipelineStatusResponse,
  PositionManagementHistoryResponse,
  PositionManagementLatestResponse,
  ReconciliationHistoryResponse,
  ReconciliationLatestResponse,
  RiskHistoryResponse,
  RiskLatestResponse,
  SignalHistoryResponse,
  SignalLatestResponse,
  StrategyHistoryResponse,
  StrategyLatestResponse,
  TradeHistoryResponse,
} from '../types/api'

interface MarketCandlesParams {
  limit?: number
  start?: string
  end?: string
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiGet<HealthResponse>('/health', signal)
}

export function getAutomationStatus(signal?: AbortSignal): Promise<AutomationStatusResponse> {
  return apiGet<AutomationStatusResponse>('/automation/status', signal)
}

export function getLatestAutomationCycle(signal?: AbortSignal): Promise<AutomationLatestCycleResponse> {
  return apiGet<AutomationLatestCycleResponse>('/automation/latest-cycle', signal)
}

export function getAutomationHistory(
  limit = 100,
  signal?: AbortSignal,
): Promise<AutomationHistoryResponse> {
  return apiGet<AutomationHistoryResponse>(`/automation/history?limit=${limit}`, signal)
}

export function getLatestPositionManagement(signal?: AbortSignal): Promise<PositionManagementLatestResponse> {
  return apiGet<PositionManagementLatestResponse>('/position-management/latest', signal)
}

export function getLatestReconciliation(signal?: AbortSignal): Promise<ReconciliationLatestResponse> {
  return apiGet<ReconciliationLatestResponse>('/reconciliation/latest', signal)
}

export function getReconciliationHistory(
  limit = 100,
  signal?: AbortSignal,
): Promise<ReconciliationHistoryResponse> {
  return apiGet<ReconciliationHistoryResponse>(`/reconciliation/history?limit=${limit}`, signal)
}

export function getPositionManagementHistory(
  limit = 100,
  signal?: AbortSignal,
): Promise<PositionManagementHistoryResponse> {
  return apiGet<PositionManagementHistoryResponse>(`/position-management/history?limit=${limit}`, signal)
}

export function getPipelineStatus(signal?: AbortSignal): Promise<PipelineStatusResponse> {
  return apiGet<PipelineStatusResponse>('/status/pipeline', signal)
}

export function getExchangeStatus(signal?: AbortSignal): Promise<ExchangeStatusResponse> {
  return apiGet<ExchangeStatusResponse>('/exchange/status', signal)
}

export function getLatestMarket(signal?: AbortSignal): Promise<MarketLatestResponse> {
  return apiGet<MarketLatestResponse>('/market/latest', signal)
}

export function getLatestFeatures(signal?: AbortSignal): Promise<FeaturesLatestResponse> {
  return apiGet<FeaturesLatestResponse>('/features/latest', signal)
}

export function getLatestInference(signal?: AbortSignal): Promise<InferenceLatestResponse> {
  return apiGet<InferenceLatestResponse>('/inference/latest', signal)
}

export function getInferenceHistory(limit = 300, signal?: AbortSignal): Promise<InferenceHistoryResponse> {
  return apiGet<InferenceHistoryResponse>(`/inference/history?limit=${limit}`, signal)
}

export function getLatestSignal(signal?: AbortSignal): Promise<SignalLatestResponse> {
  return apiGet<SignalLatestResponse>('/signals/latest', signal)
}

export function getSignalHistory(
  limit = 200,
  signal?: AbortSignal,
): Promise<SignalHistoryResponse> {
  return apiGet<SignalHistoryResponse>(`/signals/history?limit=${limit}`, signal)
}

export function getExecutionStatus(signal?: AbortSignal): Promise<ExecutionStatusResponse> {
  return apiGet<ExecutionStatusResponse>('/execution/status', signal)
}

export function getLatestStrategy(signal?: AbortSignal): Promise<StrategyLatestResponse> {
  return apiGet<StrategyLatestResponse>('/strategy/latest', signal)
}

export function getStrategyHistory(
  limit = 200,
  signal?: AbortSignal,
): Promise<StrategyHistoryResponse> {
  return apiGet<StrategyHistoryResponse>(`/strategy/history?limit=${limit}`, signal)
}

export function getLatestRisk(signal?: AbortSignal): Promise<RiskLatestResponse> {
  return apiGet<RiskLatestResponse>('/risk/latest', signal)
}

export function getRiskHistory(
  limit = 200,
  signal?: AbortSignal,
): Promise<RiskHistoryResponse> {
  return apiGet<RiskHistoryResponse>(`/risk/history?limit=${limit}`, signal)
}

export function getExecutionHistory(limit = 50, signal?: AbortSignal): Promise<ExecutionHistoryResponse> {
  return apiGet<ExecutionHistoryResponse>(`/execution/history?limit=${limit}`, signal)
}

export function getOpenPositions(signal?: AbortSignal): Promise<OpenPositionsResponse> {
  return apiGet<OpenPositionsResponse>('/positions/open', signal)
}

export function getTradeHistory(limit = 50, signal?: AbortSignal): Promise<TradeHistoryResponse> {
  return apiGet<TradeHistoryResponse>(`/trades/history?limit=${limit}`, signal)
}

export function runLatestSignalExecution(signal?: AbortSignal): Promise<ExecutionRunResponse> {
  return apiPost<ExecutionRunResponse>('/execution/run-latest-signal', undefined, signal)
}

export function getMarketCandles(
  params: MarketCandlesParams = {},
  signal?: AbortSignal,
): Promise<MarketCandlesResponse> {
  const search = new URLSearchParams()

  if (typeof params.limit === 'number' && Number.isFinite(params.limit)) {
    search.set('limit', String(params.limit))
  }
  if (typeof params.start === 'string' && params.start.trim() !== '') {
    search.set('start', params.start)
  }
  if (typeof params.end === 'string' && params.end.trim() !== '') {
    search.set('end', params.end)
  }

  const suffix = search.size > 0 ? `?${search.toString()}` : ''
  return apiGet<MarketCandlesResponse>(`/market/candles${suffix}`, signal)
}
