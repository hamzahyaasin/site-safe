import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import DataTable from '../ui/DataTable.jsx'
import { IconChevronRight } from '../ui/icons.jsx'
import { formatGas, formatTimestamp } from '../../lib/utils.js'

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
      render: (row) => <span className="font-mono text-sm font-medium text-zinc-100">{row.vest_id}</span>,
    },
    {
      key: 'worker_name',
      header: 'Assigned Worker',
      render: (row) => (
        <span className="whitespace-nowrap">{row.worker_name || <span className="text-zinc-500">Unassigned</span>}</span>
      ),
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
      key: 'gas',
      header: 'Gas',
      render: (row) => (
        <span className={`text-xs tabular-nums ${row.gas_over_limit ? 'font-semibold text-red-400' : 'text-zinc-400'}`}>
          {formatGas(row) || '—'}
        </span>
      ),
    },
    {
      key: 'gps',
      header: 'GPS',
      render: (row) => (
        <span className={`whitespace-nowrap font-mono text-xs ${row.latitude != null ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {formatGps(row)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <Badge variant={row.is_online ? 'active' : 'offline'} dot>
            {row.is_online ? 'Online' : 'Offline'}
          </Badge>
          {row.sos_active ? <Badge variant="critical">SOS</Badge> : null}
        </div>
      ),
    },
    {
      key: 'last_seen',
      header: 'Last Seen',
      render: (row) => (
        <span className="whitespace-nowrap text-xs text-zinc-500">{formatTimestamp(row.last_seen)}</span>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      cellClassName: 'text-right',
      render: (row) => (
        <Button
          variant="ghost"
          size="xs"
          onClick={(e) => {
            e.stopPropagation()
            onSelect(row)
          }}
        >
          Details
          <IconChevronRight className="h-3.5 w-3.5" />
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
      onRowClick={onSelect}
      rowClassName={(row) => (selectedId === row.id ? 'bg-amber-500/5' : undefined)}
    />
  )
}
