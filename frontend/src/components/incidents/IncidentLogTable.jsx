import { useMemo, useState } from 'react'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import DataTable from '../ui/DataTable.jsx'
import { Select } from '../ui/Input.jsx'
import Input from '../ui/Input.jsx'
import IncidentDetail from './IncidentDetail.jsx'
import {
  displayCameraId,
  exportCsv,
  formatAlertType,
  formatTimestamp,
  severityBadgeVariant,
} from '../../lib/utils.js'

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const TYPES = ['PPE_VIOLATION', 'SOS', 'ZONE_BREACH', 'INACTIVITY', 'VEHICLE_PROXIMITY']
const PAGE_SIZES = [10, 25, 50]

export default function IncidentLogTable({ alerts, loading, onResolve }) {
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState([])
  const [typeFilter, setTypeFilter] = useState([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [resolvingId, setResolvingId] = useState(null)

  const filtered = useMemo(() => {
    return alerts.filter((a) => {
      if (severityFilter.length && !severityFilter.includes(a.severity)) return false
      if (typeFilter.length && !typeFilter.includes(a.alert_type)) return false
      if (search) {
        const q = search.toLowerCase()
        const hay = `${a.worker_name} ${a.vest_id} ${a.alert_type}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      if (dateFrom) {
        if (new Date(a.timestamp) < new Date(dateFrom)) return false
      }
      if (dateTo) {
        const end = new Date(dateTo)
        end.setHours(23, 59, 59, 999)
        if (new Date(a.timestamp) > end) return false
      }
      return true
    })
  }, [alerts, severityFilter, typeFilter, search, dateFrom, dateTo])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize)

  function toggleSeverity(sev) {
    setSeverityFilter((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
    )
    setPage(1)
  }

  function toggleType(type) {
    setTypeFilter((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
    setPage(1)
  }

  async function handleResolve(id, e) {
    e?.stopPropagation()
    setResolvingId(id)
    try {
      await onResolve(id)
    } finally {
      setResolvingId(null)
    }
  }

  function handleExport() {
    exportCsv(
      `sitesafe-incidents-${new Date().toISOString().slice(0, 10)}.csv`,
      ['#', 'Timestamp', 'Worker', 'Vest ID', 'Type', 'Severity', 'Camera', 'Status', 'Source'],
      filtered.map((a, i) => [
        i + 1,
        a.timestamp,
        a.worker_name,
        a.vest_id,
        a.alert_type,
        a.severity,
        displayCameraId(a),
        a.is_resolved ? 'Resolved' : 'Open',
        a.source,
      ]),
    )
  }

  const columns = [
    {
      key: 'index',
      header: '#',
      width: 48,
      render: (_, idx) => (page - 1) * pageSize + idx + 1,
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      render: (row) => (
        <span className="whitespace-nowrap text-xs text-zinc-400">{formatTimestamp(row.timestamp)}</span>
      ),
    },
    {
      key: 'worker_name',
      header: 'Worker',
      render: (row) => row.worker_name || '—',
    },
    {
      key: 'vest_id',
      header: 'Vest ID',
      render: (row) => <span className="font-mono text-xs">{row.vest_id || '—'}</span>,
    },
    {
      key: 'alert_type',
      header: 'Type',
      render: (row) => formatAlertType(row.alert_type),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (row) => <Badge variant={severityBadgeVariant(row.severity)}>{row.severity}</Badge>,
    },
    {
      key: 'camera',
      header: 'Camera',
      render: (row) => (
        <span className="font-mono text-xs text-zinc-500">{displayCameraId(row)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) =>
        row.is_resolved ? (
          <Badge variant="success">Resolved</Badge>
        ) : (
          <Badge variant="medium">Open</Badge>
        ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) =>
        !row.is_resolved ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={resolvingId === row.id}
            onClick={(e) => handleResolve(row.id, e)}
          >
            {resolvingId === row.id ? '…' : 'Resolve'}
          </Button>
        ) : (
          <span className="text-zinc-600">—</span>
        ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-1 flex-wrap items-end gap-3">
          <Input
            label="Worker search"
            placeholder="Name or vest ID…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="min-w-[180px]"
          />
          <Input
            label="From"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
            className="w-[140px]"
          />
          <Input
            label="To"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value)
              setPage(1)
            }}
            className="w-[140px]"
          />
        </div>
        <Button variant="secondary" size="sm" onClick={handleExport}>
          Export CSV
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="self-center text-xs text-zinc-500">Severity:</span>
        {SEVERITIES.map((sev) => (
          <button
            key={sev}
            type="button"
            onClick={() => toggleSeverity(sev)}
            className={`rounded border px-2 py-1 text-[11px] font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500 ${
              severityFilter.includes(sev)
                ? 'border-amber-500/50 bg-amber-500/10 text-amber-400'
                : 'border-zinc-700 text-zinc-500 hover:border-zinc-600'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="self-center text-xs text-zinc-500">Type:</span>
        {TYPES.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => toggleType(type)}
            className={`rounded border px-2 py-1 text-[11px] font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500 ${
              typeFilter.includes(type)
                ? 'border-amber-500/50 bg-amber-500/10 text-amber-400'
                : 'border-zinc-700 text-zinc-500 hover:border-zinc-600'
            }`}
          >
            {formatAlertType(type)}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={pageData}
        loading={loading}
        emptyTitle="No incidents match filters"
        emptyDescription="Adjust filters or wait for new alerts from cameras and vests."
        expandedRowId={expandedId}
        onRowClick={(row) => setExpandedId((id) => (id === row.id ? null : row.id))}
        renderExpanded={(row) => <IncidentDetail alert={row} />}
        rowKey={(row) => row.id}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800 pt-4">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span>
            {filtered.length} incident{filtered.length !== 1 ? 's' : ''}
          </span>
          <Select
            label={null}
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(1)
            }}
            selectClassName="h-7 text-xs"
            aria-label="Page size"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n} / page
              </option>
            ))}
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-xs text-zinc-500">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
