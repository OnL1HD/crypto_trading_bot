import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from 'react'
import {
  getAutomationStatus,
  getExecutionHistory,
  getExecutionStatus,
  getExchangeStatus,
  getHealth,
  getLatestFeatures,
  getLatestInference,
  getLatestMarket,
  getLatestPositionManagement,
  getLatestReconciliation,
  getLatestRisk,
  getLatestSignal,
  getLatestStrategy,
  getMarketCandles,
  getOpenPositions,
  getPipelineStatus,
  getSignalHistory,
  getTradeHistory,
  runLatestSignalExecution,
} from '../services/dashboardApi'
import type {
  AutomationStatusResponse,
  AsyncState,
  ExecutionHistoryResponse,
  ExecutionRunResponse,
  ExecutionStatusResponse,
  ExchangeStatusResponse,
  FeaturesLatestResponse,
  HealthResponse,
  InferenceLatestResponse,
  MarketCandlesResponse,
  MarketLatestResponse,
  OpenPositionsResponse,
  PipelineStatusResponse,
  PositionManagementLatestResponse,
  ReconciliationLatestResponse,
  RiskLatestResponse,
  SignalHistoryResponse,
  SignalLatestResponse,
  StrategyLatestResponse,
  TradeHistoryResponse,
} from '../types/api'

const rawRefreshMs = Number(import.meta.env.VITE_DASHBOARD_REFRESH_MS)
const DASHBOARD_REFRESH_MS = Number.isFinite(rawRefreshMs) && rawRefreshMs >= 5000 ? rawRefreshMs : 30000

function initialAsyncState<T>(): AsyncState<T> {
  return {
    loading: true,
    data: null,
    error: null,
  }
}

async function loadCardData<T>(
  loader: (signal?: AbortSignal) => Promise<T>,
  setState: Dispatch<SetStateAction<AsyncState<T>>>,
  signal: AbortSignal,
) {
  try {
    const data = await loader(signal)
    setState({
      loading: false,
      data,
      error: null,
    })
  } catch (error) {
    if (signal.aborted) {
      return
    }

    const message = error instanceof Error ? error.message : 'Unexpected error'
    setState({
      loading: false,
      data: null,
      error: message,
    })
  }
}

export function useDashboardData() {
  const [automationState, setAutomationState] = useState<AsyncState<AutomationStatusResponse>>(() => initialAsyncState())
  const [healthState, setHealthState] = useState<AsyncState<HealthResponse>>(() => initialAsyncState())
  const [pipelineState, setPipelineState] = useState<AsyncState<PipelineStatusResponse>>(() => initialAsyncState())
  const [exchangeState, setExchangeState] = useState<AsyncState<ExchangeStatusResponse>>(() => initialAsyncState())
  const [marketState, setMarketState] = useState<AsyncState<MarketLatestResponse>>(() => initialAsyncState())
  const [featuresState, setFeaturesState] = useState<AsyncState<FeaturesLatestResponse>>(() => initialAsyncState())
  const [candlesState, setCandlesState] = useState<AsyncState<MarketCandlesResponse>>(() => initialAsyncState())
  const [inferenceState, setInferenceState] = useState<AsyncState<InferenceLatestResponse>>(() => initialAsyncState())
  const [signalState, setSignalState] = useState<AsyncState<SignalLatestResponse>>(() => initialAsyncState())
  const [strategyState, setStrategyState] = useState<AsyncState<StrategyLatestResponse>>(() => initialAsyncState())
  const [riskState, setRiskState] = useState<AsyncState<RiskLatestResponse>>(() => initialAsyncState())
  const [positionManagementState, setPositionManagementState] = useState<AsyncState<PositionManagementLatestResponse>>(() => initialAsyncState())
  const [reconciliationState, setReconciliationState] = useState<AsyncState<ReconciliationLatestResponse>>(() => initialAsyncState())
  const [signalHistoryState, setSignalHistoryState] = useState<AsyncState<SignalHistoryResponse>>(() => initialAsyncState())
  const [executionState, setExecutionState] = useState<AsyncState<ExecutionStatusResponse>>(() => initialAsyncState())
  const [executionHistoryState, setExecutionHistoryState] = useState<AsyncState<ExecutionHistoryResponse>>(() => initialAsyncState())
  const [openPositionsState, setOpenPositionsState] = useState<AsyncState<OpenPositionsResponse>>(() => initialAsyncState())
  const [tradeHistoryState, setTradeHistoryState] = useState<AsyncState<TradeHistoryResponse>>(() => initialAsyncState())
  const [runExecutionState, setRunExecutionState] = useState<AsyncState<ExecutionRunResponse>>(() => ({
    loading: false,
    data: null,
    error: null,
  }))

  const refreshDashboard = useCallback((signal: AbortSignal) => {
    void loadCardData(getHealth, setHealthState, signal)
    void loadCardData(getAutomationStatus, setAutomationState, signal)
    void loadCardData(getPipelineStatus, setPipelineState, signal)
    void loadCardData(getExchangeStatus, setExchangeState, signal)
    void loadCardData(getLatestMarket, setMarketState, signal)
    void loadCardData(getLatestFeatures, setFeaturesState, signal)
    void loadCardData((requestSignal) => getMarketCandles({ limit: 300 }, requestSignal), setCandlesState, signal)
    void loadCardData(getLatestInference, setInferenceState, signal)
    void loadCardData(getLatestSignal, setSignalState, signal)
    void loadCardData(getLatestStrategy, setStrategyState, signal)
    void loadCardData(getLatestRisk, setRiskState, signal)
    void loadCardData(getLatestPositionManagement, setPositionManagementState, signal)
    void loadCardData(getLatestReconciliation, setReconciliationState, signal)
    void loadCardData((requestSignal) => getSignalHistory(300, requestSignal), setSignalHistoryState, signal)
    void loadCardData(getExecutionStatus, setExecutionState, signal)
    void loadCardData((requestSignal) => getExecutionHistory(30, requestSignal), setExecutionHistoryState, signal)
    void loadCardData(getOpenPositions, setOpenPositionsState, signal)
    void loadCardData((requestSignal) => getTradeHistory(30, requestSignal), setTradeHistoryState, signal)
  }, [])

  useEffect(() => {
    let active = true
    let activeController: AbortController | null = null

    const refresh = () => {
      if (!active) {
        return
      }

      if (activeController !== null) {
        activeController.abort()
      }

      const controller = new AbortController()
      activeController = controller
      refreshDashboard(controller.signal)
    }

    refresh()
    const refreshTimer = window.setInterval(refresh, DASHBOARD_REFRESH_MS)

    return () => {
      active = false
      window.clearInterval(refreshTimer)
      if (activeController !== null) {
        activeController.abort()
      }
    }
  }, [refreshDashboard])

  const handleRunLatestSignal = useCallback(async () => {
    setRunExecutionState({ loading: true, data: null, error: null })

    try {
      const data = await runLatestSignalExecution()
      setRunExecutionState({ loading: false, data, error: null })
      const controller = new AbortController()
      refreshDashboard(controller.signal)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unexpected error'
      setRunExecutionState({ loading: false, data: null, error: message })
    }
  }, [refreshDashboard])

  return {
    candlesState,
    exchangeState,
    executionHistoryState,
    executionState,
    featuresState,
    healthState,
    automationState,
    inferenceState,
    marketState,
    openPositionsState,
    pipelineState,
    positionManagementState,
    reconciliationState,
    runExecutionState,
    riskState,
    signalHistoryState,
    signalState,
    strategyState,
    tradeHistoryState,
    handleRunLatestSignal,
  }
}
