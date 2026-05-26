import { useCallback, useEffect, useState, type CSSProperties, type Dispatch, type SetStateAction } from 'react'
import heroSectionImage from '../../images/hero_section.png'
import { AppShell } from '../components/layout/AppShell'
import DecryptedText from '../components/hero/DecryptedText'
import { BacktestSummaryCard } from '../components/cards/BacktestSummaryCard'
import { ExecutionActivityCard } from '../components/cards/ExecutionActivityCard'
import { ExecutionStatusCard } from '../components/cards/ExecutionStatusCard'
import { LatestPredictionCard } from '../components/cards/LatestPredictionCard'
import { MarketOverviewCard } from '../components/cards/MarketOverviewCard'
import { OpenPositionsCard } from '../components/cards/OpenPositionsCard'
import { SystemStatusCard } from '../components/cards/SystemStatusCard'
import { MarketPriceChart } from '../components/charts/MarketPriceChart'
import { SystemOverviewSection } from '../components/sections/SystemOverviewSection'
import {
  getExecutionHistory,
  getExecutionStatus,
  getExchangeStatus,
  getHealth,
  getAutomationStatus,
  getLatestSignal,
  getLatestStrategy,
  getMarketCandles,
  getLatestFeatures,
  getLatestInference,
  getLatestMarket,
  getLatestReconciliation,
  getOpenPositions,
  getSignalHistory,
  getPipelineStatus,
  getTradeHistory,
} from '../services/dashboardApi'
import type {
  AsyncState,
  AutomationStatusResponse,
  ExecutionHistoryResponse,
  ExecutionStatusResponse,
  ExchangeStatusResponse,
  FeaturesLatestResponse,
  HealthResponse,
  InferenceLatestResponse,
  MarketCandlesResponse,
  MarketLatestResponse,
  OpenPositionsResponse,
  PipelineStatusResponse,
  ReconciliationLatestResponse,
  SignalHistoryResponse,
  SignalLatestResponse,
  StrategyLatestResponse,
  TradeHistoryResponse,
} from '../types/api'

const rawRefreshMs = Number(import.meta.env.VITE_DASHBOARD_REFRESH_MS)
const DASHBOARD_REFRESH_MS = Number.isFinite(rawRefreshMs) && rawRefreshMs >= 5000 ? rawRefreshMs : 30000
const HERO_SECTION_HEIGHT = '100dvh'
const HERO_STYLE = { '--hero-height': HERO_SECTION_HEIGHT } as CSSProperties

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

export function DashboardPage() {
  const handleScrollToChart = useCallback(() => {
    document.getElementById('market-chart-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const handleScrollToPerformance = useCallback(() => {
    document.getElementById('dashboard-overview-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const [healthState, setHealthState] = useState<AsyncState<HealthResponse>>(() =>
    initialAsyncState<HealthResponse>(),
  )
  const [automationState, setAutomationState] = useState<AsyncState<AutomationStatusResponse>>(() =>
    initialAsyncState<AutomationStatusResponse>(),
  )
  const [pipelineState, setPipelineState] = useState<AsyncState<PipelineStatusResponse>>(() =>
    initialAsyncState<PipelineStatusResponse>(),
  )
  const [exchangeState, setExchangeState] = useState<AsyncState<ExchangeStatusResponse>>(() =>
    initialAsyncState<ExchangeStatusResponse>(),
  )
  const [marketState, setMarketState] = useState<AsyncState<MarketLatestResponse>>(() =>
    initialAsyncState<MarketLatestResponse>(),
  )
  const [featuresState, setFeaturesState] = useState<AsyncState<FeaturesLatestResponse>>(() =>
    initialAsyncState<FeaturesLatestResponse>(),
  )
  const [candlesState, setCandlesState] = useState<AsyncState<MarketCandlesResponse>>(() =>
    initialAsyncState<MarketCandlesResponse>(),
  )
  const [inferenceState, setInferenceState] = useState<AsyncState<InferenceLatestResponse>>(() =>
    initialAsyncState<InferenceLatestResponse>(),
  )
  const [signalState, setSignalState] = useState<AsyncState<SignalLatestResponse>>(() =>
    initialAsyncState<SignalLatestResponse>(),
  )
  const [strategyState, setStrategyState] = useState<AsyncState<StrategyLatestResponse>>(() =>
    initialAsyncState<StrategyLatestResponse>(),
  )
  const [reconciliationState, setReconciliationState] = useState<AsyncState<ReconciliationLatestResponse>>(() =>
    initialAsyncState<ReconciliationLatestResponse>(),
  )
  const [signalHistoryState, setSignalHistoryState] = useState<AsyncState<SignalHistoryResponse>>(() =>
    initialAsyncState<SignalHistoryResponse>(),
  )
  const [executionState, setExecutionState] = useState<AsyncState<ExecutionStatusResponse>>(() =>
    initialAsyncState<ExecutionStatusResponse>(),
  )
  const [executionHistoryState, setExecutionHistoryState] = useState<AsyncState<ExecutionHistoryResponse>>(() =>
    initialAsyncState<ExecutionHistoryResponse>(),
  )
  const [openPositionsState, setOpenPositionsState] = useState<AsyncState<OpenPositionsResponse>>(() =>
    initialAsyncState<OpenPositionsResponse>(),
  )
  const [tradeHistoryState, setTradeHistoryState] = useState<AsyncState<TradeHistoryResponse>>(() =>
    initialAsyncState<TradeHistoryResponse>(),
  )

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
      const { signal } = controller

      refreshDashboard(signal)
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

  return (
    <>
      <section id="hero-section" className="dashboard-hero" aria-label="Hero background section" style={HERO_STYLE}>
        <div className="dashboard-hero__bg" aria-hidden="true">
          <div className="dashboard-hero__bg-base" />
          <div className="dashboard-hero__bg-glow dashboard-hero__bg-glow--violet" />
          <div className="dashboard-hero__bg-glow dashboard-hero__bg-glow--blue" />
          <div className="dashboard-hero__bg-rings" />
          <div className="dashboard-hero__bg-particles" />
          <div className="dashboard-hero__bg-vignette" />
        </div>
        <div className="dashboard-hero__content">
          <div className="dashboard-hero__image-frame">
            <img className="dashboard-hero__image" src={heroSectionImage} alt="Trading Garden hero" />
          </div>
          <div className="dashboard-hero__copy">
            <div className="dashboard-hero__kicker">
              <span className="dashboard-hero__kicker-line" />
              <span className="dashboard-hero__kicker-star" aria-hidden="true" />
              <span>Autonomous trading bot</span>
              <span className="dashboard-hero__kicker-line" />
            </div>
            <DecryptedText
              text="Trading Garden"
              speed={150}
              maxIterations={10}
              sequential
              animateOn="inViewHover"
              className="text-[var(--text-primary)]"
              encryptedClassName="text-[var(--text-secondary)]"
              parentClassName="hero-brand-text dashboard-hero__title text-[clamp(1.05rem,3.3vw,2.6rem)] font-semibold tracking-[0.1em]"
            />
            <p className="dashboard-hero__description">
              A cinematic control surface for live market structure, model conviction, and guarded demo
              execution in one calm view.
            </p>
            <div className="dashboard-hero__pill-row" aria-label="Hero highlights">
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M1.5 8h2l1.1-2.2L6.7 11l1.9-6 1.6 3H14.5" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span>Live signals</span>
              </div>
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M8 1.8 12.7 3.8v3.5c0 3-2 5.8-4.7 6.9C5.3 13.1 3.3 10.3 3.3 7.3V3.8L8 1.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                    <path d="m6.3 8 1.2 1.2 2.2-2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span>Guarded execution</span>
              </div>
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M5 2.3v11.4M11 2.3v11.4M2.3 5h11.4M2.3 11h11.4" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
                    <circle cx="5" cy="5" r="1.1" fill="currentColor" />
                    <circle cx="11" cy="8" r="1.1" fill="currentColor" />
                    <circle cx="5" cy="11" r="1.1" fill="currentColor" />
                  </svg>
                </span>
                <span>Autonomous strategies</span>
              </div>
            </div>
            <div className="dashboard-hero__actions">
              <button type="button" className="hero-glow-button" onClick={handleScrollToChart}>
                <span>Explore the chart</span>
                <span className="hero-button__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M3 8h9" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
                    <path d="m8.8 3.8 4.2 4.2-4.2 4.2" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </button>
              <button type="button" className="hero-secondary-button" onClick={handleScrollToPerformance}>
                <span>View performance</span>
                <span className="hero-button__icon hero-button__icon--bars" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M3 12.7V9.2M8 12.7V5.5M13 12.7V2.8" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <SystemOverviewSection />

      <AppShell>
        <section id="dashboard-overview-section" className="cards-grid" aria-label="Dashboard cards">
          <MarketOverviewCard marketState={marketState} featuresState={featuresState} />
          <LatestPredictionCard inferenceState={inferenceState} signalState={signalState} strategyState={strategyState} />
          <SystemStatusCard
            healthState={healthState}
            pipelineState={pipelineState}
            exchangeState={exchangeState}
            automationState={automationState}
            reconciliationState={reconciliationState}
          />
          <BacktestSummaryCard />
        </section>

        <section id="market-chart-section" aria-label="Market chart section">
          <MarketPriceChart
            candlesState={candlesState}
            signalHistoryState={signalHistoryState}
            signalState={signalState}
          />
        </section>

        <section className="cards-grid execution-cards-grid" aria-label="Execution dashboard cards">
          <ExecutionStatusCard executionState={executionState} />
          <OpenPositionsCard positionsState={openPositionsState} />
        </section>

        <ExecutionActivityCard
          executionHistoryState={executionHistoryState}
          tradeHistoryState={tradeHistoryState}
        />
      </AppShell>
    </>
  )
}
