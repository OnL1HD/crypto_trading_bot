import { ExecutionActivityCard } from '../components/cards/ExecutionActivityCard'
import { AppShell } from '../components/layout/AppShell'
import { ExecutionCoreSection } from '../components/sections/ExecutionCoreSection'
import { useDashboardData } from '../hooks/useDashboardData'

export function ExecutionPage() {
  const {
    executionHistoryState,
    executionState,
    openPositionsState,
    positionManagementState,
    tradeHistoryState,
  } = useDashboardData()

  return (
    <AppShell className="execution-page-shell">
      <ExecutionCoreSection
        executionState={executionState}
        openPositionsState={openPositionsState}
        positionManagementState={positionManagementState}
      />

      <ExecutionActivityCard
        executionHistoryState={executionHistoryState}
        tradeHistoryState={tradeHistoryState}
      />
    </AppShell>
  )
}
