import { useWorkers } from '../hooks/useWorkers.js'
import WorkerStatusGrid from '../components/dashboard/WorkerStatusGrid.jsx'

export default function WorkersPage() {
  const { workers, loading, highlightIds } = useWorkers()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-100">Workers</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {workers.length} registered · {workers.filter((w) => w.is_active).length} active on site
        </p>
      </header>
      <WorkerStatusGrid workers={workers} loading={loading} highlightIds={highlightIds} />
    </div>
  )
}
