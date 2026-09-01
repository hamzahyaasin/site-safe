import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import DataTable from '../ui/DataTable.jsx'
import { formatTimestamp } from '../../lib/utils.js'

function batteryBarClass(level) {
  if (level == null) return 'bg-zinc-600'
  if (level < 20) return 'bg-red-500'
  if (level < 40) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function formatGps(vest) {
  if (vest.latitude != null && vest.longitude != null) {
    return `${vest.latitude.toFixed(5)}, ${vest.longitude.toFixed(5)}`
  }
  return vest.is_online ? 'Awaiting fix…' : 'No fix'
}

export default function VestTable({ vests, loading, selectedId, onSelect }) {
  const columns = [
    {
      key: 'vest_id',
      header: 'Vest ID',
      render: (row) => <span className="font-mono text-sm text-amber-400/90">{row.vest_id}</span>,
    },
    {
      key: 'worker_name',
      header: 'Assigned Worker',
      render: (row) => row.worker_name || <span className="text-zinc-600">Unassigned</span>,
    },
    {
      key: 'battery',
      header: 'Battery',
      render: (row) => {
        const pct = row.battery_level == null ? 0 : Math.max(0, Math.min(100, row.battery_level))
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-zinc-800">
              <div className={`h-full rounded-full ${batteryBarClass(row.battery_level)}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs tabular-nums text-zinc-400">
              {row.battery_level == null ? '—' : `${pct}%`}
            </span>
          </div>
        )
      },
    },
    {
      key: 'gps',
      header: 'GPS',
      render: (row) => (
        <span className={`font-mono text-xs ${row.latitude != null ? 'text-zinc-400' : 'text-zinc-600'}`}>
          {formatGps(row)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <Badge variant={row.is_online ? 'active' : 'offline'}>{row.is_online ? 'Online' : 'Offline'}</Badge>
          {row.sos_active ? <Badge variant="critical">SOS</Badge> : null}
        </div>
      ),
    },
    {
      key: 'last_seen',
      header: 'Last Seen',
      render: (row) => (
        <span className="text-xs text-zinc-500">{formatTimestamp(row.last_seen)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <Button variant="ghost" size="sm" onClick={() => onSelect(row)}>
          {selectedId === row.id ? 'Selected' : 'View'}
        </Button>
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      data={vests}
      loading={loading}
      emptyTitle="No smart vests registered"
      emptyDescription="Register a vest to start tracking telemetry."
      rowKey={(row) => row.id}
      rowClassName={(row) =>
        selectedId === row.id ? 'bg-amber-500/5 border-l-2 border-l-amber-500' : undefined
      }
    />
  )
}
