import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Alert from '../components/ui/Alert.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Input, { Checkbox } from '../components/ui/Input.jsx'
import { SegmentedControl } from '../components/ui/FilterChip.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { IconDownload, IconReport } from '../components/ui/icons.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'
import { browserTimeZone, cn } from '../lib/utils.js'
import { useReports } from '../hooks/useReports.js'
import { useAuth } from '../context/AuthContext.jsx'

const REPORT_TYPES = [
  { id: 'INCIDENT', label: 'Incident Report', description: 'All alerts and incidents in the selected period' },
  {
    id: 'COMPLIANCE',
    label: 'Safety Performance Report',
    description: 'Incidents, PPE violations, violation-free days and response time by zone',
  },
]

const FORMATS = [
  { id: 'PDF', label: 'PDF' },
  { id: 'DOCX', label: 'Word (.docx)' },
]

function localIsoDate(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function defaultDateRange() {
  const dateTo = new Date()
  const dateFrom = new Date()
  dateFrom.setDate(dateFrom.getDate() - 30)
  return {
    date_from: localIsoDate(dateFrom),
    date_to: localIsoDate(dateTo),
  }
}

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
]

function rangeForDays(days) {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - days)
  return { date_from: localIsoDate(from), date_to: localIsoDate(to) }
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function ReportsPage() {
  const { canOperate, role } = useAuth()
  if (role && !canOperate) {
    return (
      <div className="space-y-6">
        <PageHeader title="Reports" description="Generate and download incident and compliance reports" />
        <EmptyState
          icon={IconReport}
          title="Reports need the Safety Officer or Admin role"
          description="Ask an Admin to change your role if you need to generate or download reports."
        />
      </div>
    )
  }
  return <ReportsWorkspace />
}

function ReportsWorkspace() {
  const { reports, loading, generating, error, generateReport, downloadReport } = useReports()
  const { toast } = useFeedback()
  const [downloadingId, setDownloadingId] = useState(null)

  async function handleDownload(report) {
    setDownloadingId(report.id)
    try {
      await downloadReport(report)
    } catch (err) {
      toast(apiErrorText(err, 'Could not download the report. The file may have been removed from the server.'), 'error')
    } finally {
      setDownloadingId(null)
    }
  }
  const [reportType, setReportType] = useState('INCIDENT')
  const [{ date_from, date_to }, setDateRange] = useState(defaultDateRange)
  const [fileFormat, setFileFormat] = useState('PDF')
  const [includeEvidence, setIncludeEvidence] = useState(true)
  const [formError, setFormError] = useState('')

  async function handleGenerate(e) {
    e.preventDefault()
    setFormError('')

    if (date_from > date_to) {
      setFormError('End date must be on or after start date.')
      return
    }

    try {
      const filename = await generateReport({
        report_type: reportType,
        date_from,
        date_to,
        file_format: fileFormat,
        tz: browserTimeZone(),
        include_evidence: includeEvidence,
      })
      toast(`Report generated: ${filename}. Download it from the list below.`)
    } catch (err) {
      setFormError(err.message || 'Failed to generate report')
    }
  }

  const columns = [
    { key: 'created_at', header: 'Generated', render: (row) => formatDate(row.created_at) },
    {
      key: 'type',
      header: 'Report',
      render: (row) => (
        <>
          {row.report_type_label || row.report_type}
          <span className="block text-[11px] text-zinc-500">
            {row.file_format || 'DOCX'} · {row.includes_evidence ? 'with snapshots' : 'no snapshots'}
          </span>
        </>
      ),
    },
    {
      key: 'period',
      header: 'Period',
      cellClassName: 'whitespace-nowrap',
      render: (row) => `${row.date_from} → ${row.date_to}`,
    },
    {
      key: 'filename',
      header: 'File',
      className: 'hidden lg:table-cell',
      cellClassName: 'hidden lg:table-cell',
      render: (row) => <code className="break-all text-xs text-zinc-400">{row.filename}</code>,
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      cellClassName: 'text-right',
      render: (row) => (
        <Button variant="secondary" size="xs" loading={downloadingId === row.id} onClick={() => handleDownload(row)}>
          {downloadingId === row.id ? null : <IconDownload className="h-3.5 w-3.5" />}
          Download
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Generate and download incident and compliance reports" />

      <Card>
        <CardHeader>
          <CardTitle>Generate Report</CardTitle>
          <CardDescription>Choose a report type and date range</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleGenerate}>
            <fieldset>
              <legend className="mb-2 text-xs font-medium text-zinc-300">Report type</legend>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {REPORT_TYPES.map((type) => (
                  <label
                    key={type.id}
                    className={cn(
                      'flex cursor-pointer flex-col gap-1 rounded-lg border px-3.5 py-3 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-amber-500',
                      reportType === type.id
                        ? 'border-amber-500/60 bg-amber-500/[0.06] shadow-[inset_0_0_0_1px_rgba(245,158,11,0.25)]'
                        : 'border-zinc-700 hover:border-zinc-500 hover:bg-zinc-800/30',
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="report_type"
                        value={type.id}
                        checked={reportType === type.id}
                        onChange={() => setReportType(type.id)}
                      />
                      <span className="text-sm font-medium text-zinc-100">{type.label}</span>
                    </span>
                    <span className="pl-6 text-xs text-zinc-400">{type.description}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
              <div className="flex flex-col gap-1.5">
                <div className="flex flex-wrap items-end gap-3">
                  <Input
                    label="From"
                    type="date"
                    value={date_from}
                    max={date_to}
                    onChange={(e) => setDateRange((d) => ({ ...d, date_from: e.target.value }))}
                    className="w-[160px]"
                    required
                  />
                  <Input
                    label="To"
                    type="date"
                    value={date_to}
                    min={date_from}
                    onChange={(e) => setDateRange((d) => ({ ...d, date_to: e.target.value }))}
                    className="w-[160px]"
                    required
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {PRESETS.map((p) => (
                    <button
                      key={p.days}
                      type="button"
                      onClick={() => setDateRange(rangeForDays(p.days))}
                      className="rounded px-1.5 py-0.5 text-[11px] font-medium text-amber-400 hover:bg-amber-500/10 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-medium text-zinc-300">Format</span>
                <SegmentedControl
                  label="Format"
                  value={fileFormat}
                  onChange={setFileFormat}
                  options={FORMATS.map((f) => ({ value: f.id, label: f.label }))}
                />
              </div>
            </div>
            <p className="-mt-2 text-[11px] text-zinc-500">
              Days run midnight to midnight in your time zone ({browserTimeZone() || 'UTC'}).
            </p>

            <Checkbox
              label="Include evidence snapshots"
              hint={`${
                reportType === 'INCIDENT'
                  ? 'The camera frames of the most severe incidents (up to 24), each captioned and referenced from the incident log.'
                  : 'Up to two camera frames per zone, its most severe incidents first.'
              } Frames can show people; leave them out for a report shared widely.`}
              checked={includeEvidence}
              onChange={(e) => setIncludeEvidence(e.target.checked)}
            />

            {formError ? <Alert>{formError}</Alert> : null}
            {error ? <Alert>{error}</Alert> : null}

            <div className="flex items-center gap-3 border-t border-zinc-800 pt-4">
              <Button type="submit" variant="primary" loading={generating}>
                {generating ? 'Generating…' : 'Generate report'}
              </Button>
              {generating ? <span className="text-xs text-zinc-500">This can take a few seconds with snapshots.</span> : null}
            </div>
          </form>
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-zinc-100">Generated reports</h2>
        <DataTable
          columns={columns}
          data={reports}
          loading={loading}
          minWidthClass="min-w-[560px]"
          emptyTitle="No reports generated yet"
          emptyDescription="Generate one above; it will be listed here to download again later."
          rowKey={(row) => row.id}
        />
      </div>
    </div>
  )
}
