import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import DataTable from '../ui/DataTable.jsx'
import FilterChip, { SegmentedControl } from '../ui/FilterChip.jsx'
import { Select } from '../ui/Input.jsx'
import Input from '../ui/Input.jsx'
import PageHeader from '../ui/PageHeader.jsx'
import { IconCheck, IconChevronRight, IconDownload, IconSearch } from '../ui/icons.jsx'
import IncidentDetail from './IncidentDetail.jsx'
import { apiErrorText, useFeedback } from '../../context/FeedbackContext.jsx'
import {
  alertSubject,
  alertTypeTitle,
  cn,
  displayCameraId,
  exportCsv,
  formatTimestamp,
  severityBadgeVariant,
} from '../../lib/utils.js'

const STATUSES = ['all', 'open', 'resolved']

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const TYPES = ['PPE_VIOLATION', 'FALL', 'FIRE', 'SMOKE', 'DANGER_AREA', 'SOS', 'GAS', 'ZONE_BREACH', 'INACTIVITY', 'VEHICLE_PROXIMITY']
const PAGE_SIZES = [10, 25, 50]

export default function IncidentLogTable({ alerts, loading, onResolve }) {
  const { toast } = useFeedback()
  // Status lives in the address (?status=open) so the bell and dashboard can link to open incidents.
  const [params, setParams] = useSearchParams()
  const status = STATUSES.includes(params.get('status')) ? params.get('status') : 'all'
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
      if (status === 'open' && a.is_resolved) return false
      if (status === 'resolved' && !a.is_resolved) return false
      if (severityFilter.length && !severityFilter.includes(a.severity)) return false
      if (typeFilter.length && !typeFilter.includes(a.alert_type)) return false
      if (search) {
        const q = search.toLowerCase()
        const hay = `${a.worker_name ?? ''} ${a.zone_name ?? ''} ${a.vest_id ?? ''} ${alertTypeTitle(a.alert_type)} ${a.camera_id ?? ''}`.toLowerCase()
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
  }, [alerts, status, severityFilter, typeFilter, search, dateFrom, dateTo])

  const openCount = alerts.filter((a) => !a.is_resolved).length
  const filtersActive = Boolean(search || dateFrom || dateTo || severityFilter.length || typeFilter.length)

  function setStatus(next) {
    setParams(next === 'all' ? {} : { status: next }, { replace: true })
    setPage(1)
  }

  function clearFilters() {
    setSearch('')
    setDateFrom('')
    setDateTo('')
    setSeverityFilter([])
    setTypeFilter([])
    setPage(1)
  }

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  // A filter or a resolve can shrink the list below the current page.
  const currentPage = Math.min(page, totalPages)
  const pageData = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize)

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
      toast('Incident resolved')
    } catch (err) {
      toast(apiErrorText(err, 'Could not resolve the incident'), 'error')
    } finally {
      setResolvingId(null)
    }
  }

  function handleExport() {
    exportCsv(
      `sitesafe-incidents-${new Date().toISOString().slice(0, 10)}.csv`,
      ['#', 'Timestamp', 'Worker', 'Zone', 'Vest ID', 'Type', 'Severity', 'Camera', 'Status', 'Source'],
      filtered.map((a, i) => [
        i + 1,
        a.timestamp,
        a.worker_name,
        a.zone_name,
        a.vest_id,
        alertTypeTitle(a.alert_type),
        a.severity,
        displayCameraId(a),
        a.is_resolved ? 'Resolved' : 'Open',
        a.source,
      ]),
    )
  }

  const columns = [
    {
      key: 'expand',
      header: <span className="sr-only">Details</span>,
      width: 36,
      cellClassName: 'pr-0',
      render: (row) => (
        <IconChevronRight
          className={cn('h-4 w-4 text-zinc-500 transition-transform', expandedId === row.id && 'rotate-90 text-amber-400')}
        />
      ),
    },
    {
      key: 'index',
      header: '#',
      width: 48,
      cellClassName: 'tabular-nums text-zinc-500',
      render: (_, idx) => (currentPage - 1) * pageSize + idx + 1,
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
      header: 'Worker / zone',
      render: (row) => (
        <div className="min-w-0">
          <div className="truncate">{row.worker_name || (row.zone ? alertSubject(row) : '—')}</div>
          {row.vest_id ? <div className="font-mono text-[11px] text-zinc-500">{row.vest_id}</div> : null}
        </div>
      ),
    },
    {
      key: 'alert_type',
      header: 'Type',
      render: (row) => (
        <span className="flex items-center gap-2 whitespace-nowrap font-medium text-zinc-100">
          {alertTypeTitle(row.alert_type)}
          {row.source === 'SIMULATED' ? <Badge variant="neutral">Sim</Badge> : null}
        </span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (row) => <Badge variant={severityBadgeVariant(row.severity)}>{row.severity}</Badge>,
    },
    {
      key: 'camera',
      header: 'Camera',
      // Shown on wide screens; the expanded detail and the CSV always include it.
      className: 'hidden xl:table-cell',
      cellClassName: 'hidden xl:table-cell',
      render: (row) => (
        <span className="font-mono text-xs text-zinc-500">{displayCameraId(row)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) =>
        row.is_resolved ? (
          <Badge variant="success" dot>
            Resolved
          </Badge>
        ) : (
          <Badge variant="atRisk" dot>
            Open
          </Badge>
        ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      className: 'text-right',
      cellClassName: 'text-right',
      render: (row) =>
        !row.is_resolved && onResolve ? (
          <Button
            variant="secondary"
            size="xs"
            loading={resolvingId === row.id}
            onClick={(e) => handleResolve(row.id, e)}
          >
            {resolvingId === row.id ? null : <IconCheck className="h-3 w-3" />}
            Resolve
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader
        title="Incident Log"
        description="Full audit trail of safety incidents from cameras, vests, and simulations"
        actions={
          <Button variant="secondary" size="sm" onClick={handleExport} disabled={!filtered.length}>
            <IconDownload className="h-3.5 w-3.5" />
            Export CSV
          </Button>
        }
      />

      <div className="space-y-4 rounded-xl border border-zinc-800 bg-[#151821] p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
            <Input
              label="Search"
              placeholder="Worker, vest or type…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              inputClassName="pl-8"
              type="search"
            />
            <IconSearch className="pointer-events-none absolute bottom-2.5 left-2.5 h-4 w-4 text-zinc-500" />
          </div>
          <Input
            label="From"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
            className="w-[150px]"
          />
          <Input
            label="To"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => {
              setDateTo(e.target.value)
              setPage(1)
            }}
            className="w-[150px]"
          />
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-zinc-300">Status</span>
            <SegmentedControl
              label="Status"
              value={status}
              onChange={setStatus}
              options={[
                { value: 'all', label: 'All', count: alerts.length },
                { value: 'open', label: 'Open', count: openCount },
                { value: 'resolved', label: 'Resolved', count: alerts.length - openCount },
              ]}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2.5 border-t border-zinc-800 pt-4">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="w-16 text-xs font-medium text-zinc-500">Severity</span>
            {SEVERITIES.map((sev) => (
              <FilterChip key={sev} selected={severityFilter.includes(sev)} onClick={() => toggleSeverity(sev)}>
                {sev.charAt(0) + sev.slice(1).toLowerCase()}
              </FilterChip>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="w-16 text-xs font-medium text-zinc-500">Type</span>
            {TYPES.map((type) => (
              <FilterChip key={type} selected={typeFilter.includes(type)} onClick={() => toggleType(type)}>
                {alertTypeTitle(type)}
              </FilterChip>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 text-xs text-zinc-500">
        <span>
          Showing <span className="font-medium tabular-nums text-zinc-300">{filtered.length}</span> of{' '}
          <span className="tabular-nums">{alerts.length}</span> incidents · click a row for details and evidence
        </span>
        {filtersActive ? (
          <Button variant="ghost" size="xs" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
      </div>

      <DataTable
        columns={columns}
        data={pageData}
        loading={loading}
        emptyTitle={alerts.length ? 'No incidents match these filters' : 'No incidents recorded yet'}
        emptyDescription={
          alerts.length
            ? 'Clear or change the filters to see more.'
            : 'Alerts from cameras, vests and the simulator appear here.'
        }
        expandedRowId={expandedId}
        onRowClick={(row) => setExpandedId((id) => (id === row.id ? null : row.id))}
        renderExpanded={(row) => <IncidentDetail alert={row} />}
        minWidthClass="min-w-[640px]"
        rowKey={(row) => row.id}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span>Rows per page</span>
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
                {n}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
            Previous
          </Button>
          <span className="px-1 text-xs tabular-nums text-zinc-400">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={currentPage >= totalPages}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
