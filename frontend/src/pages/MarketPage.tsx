import { AppShell } from '../components/layout/AppShell'
import { MarketOverviewCard } from '../components/cards/MarketOverviewCard'
import { MarketPriceChart } from '../components/charts/MarketPriceChart'
import { useDashboardData } from '../hooks/useDashboardData'

export function MarketPage() {
  const { candlesState, featuresState, marketState, signalHistoryState, signalState } = useDashboardData()

  return (
    <div className="market-page-shell">
      <AppShell>
        <section className="market-page-panel" aria-label="Market overview region">
          <div className="cards-grid cards-grid--market" aria-label="Market overview cards">
            <MarketOverviewCard marketState={marketState} featuresState={featuresState} />
          </div>
        </section>

        <section className="market-page-panel market-page-panel--chart" aria-label="Market chart region">
          <MarketPriceChart
            candlesState={candlesState}
            signalHistoryState={signalHistoryState}
            signalState={signalState}
          />
        </section>
      </AppShell>
    </div>
  )
}
