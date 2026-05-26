import signalImage from '../../images/Signal_image.png'
import treeImage from '../../images/tree_image.png'
import { LatestPredictionCard } from '../components/cards/LatestPredictionCard'
import { LatestRiskDecisionCard } from '../components/cards/LatestRiskDecisionCard'
import { AppShell } from '../components/layout/AppShell'
import { useDashboardData } from '../hooks/useDashboardData'

export function ModelPage() {
  const { inferenceState, riskState, signalState, strategyState } = useDashboardData()

  return (
    <div className="model-page-shell">
      <AppShell>
        <section className="model-page-grid" aria-label="Model insights cards and diagrams">
          <LatestPredictionCard
            inferenceState={inferenceState}
            signalState={signalState}
            strategyState={strategyState}
          />

          <figure className="model-page-media model-page-media--signal">
            <div className="model-page-media__frame">
              <img className="model-page-media__image" src={signalImage} alt="Signal decision flow illustration" />
            </div>
          </figure>

          <figure className="model-page-media model-page-media--tree">
            <div className="model-page-media__frame">
              <img className="model-page-media__image" src={treeImage} alt="Model decision tree illustration" />
            </div>
          </figure>

          <LatestRiskDecisionCard riskState={riskState} />
        </section>
      </AppShell>
    </div>
  )
}
