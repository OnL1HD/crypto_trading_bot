import { ModelRuntimeCard } from '../components/cards/ModelRuntimeCard'
import { SystemStatusCard } from '../components/cards/SystemStatusCard'
import { AppShell } from '../components/layout/AppShell'
import { useDashboardData } from '../hooks/useDashboardData'

export function SystemPage() {
  const { automationState, exchangeState, healthState, inferenceState, pipelineState, reconciliationState } = useDashboardData()

  return (
    <AppShell>
      <section className="cards-grid" aria-label="System status cards">
        <SystemStatusCard
          healthState={healthState}
          pipelineState={pipelineState}
          exchangeState={exchangeState}
          automationState={automationState}
          reconciliationState={reconciliationState}
        />
        <ModelRuntimeCard inferenceState={inferenceState} />
      </section>
    </AppShell>
  )
}
