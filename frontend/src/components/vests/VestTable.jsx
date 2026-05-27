import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import DataTable from '../ui/DataTable.jsx'
import { formatTimestamp } from '../../lib/utils.js'

function vestStatus(worker) {
  if (!worker?.is_active) return { label: 'Offline', variant: 'offline' }
  return { label: 'Online', variant: 'active' }
}

function deriveBattery(worker) {
  return 40 + ((worker.id * 13) % 55)
}

function deriveLastPing(worker) {
  return worker.created_at
}

export default function VestTable({ workers, loading, selectedId, onSelect, onAssign, onUnassign }) {
  const columns = [
    {
      key: 'vest_id',
      header: 'Vest ID',
      render: (row) => <span className="font-mono text-sm text-amber-400/90">{row.vest_id}</span>,
    },
    {
      key: 'name',
      header: 'Assigned Worker',
      render: (row) => row.name || <span className="text-zinc-600">Unassigned</span>,
    },
    {
      key: 'last_ping',
      header: 'Last Ping',
      render: (row) => (
        <span className="text-xs text-zinc-500">{formatTimestamp(deriveLastPing(row))}</span>
      ),
    },
    {
      key: 'battery',
      header: 'Battery %',
      render: (row) => {
        const pct = deriveBattery(row)
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-zinc-800">
              <div
                className={`h-full rounded-full ${pct < 20 ? 'bg-red-500' : pct < 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs tabular-nums text-zinc-400">{pct}%</span>
          </div>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => {
        const s = vestStatus(row)
        return <Badge variant={s.variant}>{s.label}</Badge>
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => onSelect(row)}>
            {selectedId === row.id ? 'Selected' : 'View'}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onAssign(row)}>
            Assign
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onUnassign(row)}>
            Unassign
          </Button>
        </div>
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      data={workers}
      loading={loading}
      emptyTitle="No vests registered"
      emptyDescription="Register a vest by adding a worker with a vest ID."
      rowKey={(row) => row.id}
      rowClassName={(row) =>
        selectedId === row.id ? 'bg-amber-500/5 border-l-2 border-l-amber-500' : undefined
      }
    />
  )
}
