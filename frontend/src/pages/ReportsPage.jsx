import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Input from '../components/ui/Input.jsx'
import { cn } from '../lib/utils.js'
import { useReports } from '../hooks/useReports.js'

const REPORT_TYPES = [
  { id: 'INCIDENT', label: 'Incident Report', description: 'All alerts and incidents in the selected period' },
  {
    id: 'COMPLIANCE',
    label: 'Compliance Report',
    description: 'Worker activity, PPE compliance, and resolution summary',
  },
]

function defaultDateRange() {
  const dateTo = new Date()
  const dateFrom = new Date()
  dateFrom.setDate(dateFrom.getDate() - 30)
  return {
    date_from: dateFrom.toISOString().slice(0, 10),
    date_to: dateTo.toISOString().slice(0, 10),
  }
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
  const { reports, loading, generating, error, generateReport, downloadReport } = useReports()
  const [reportType, setReportType] = useState('INCIDENT')
  const [{ date_from, date_to }, setDateRange] = useState(defaultDateRange)
  const [formError, setFormError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  async function handleGenerate(e) {
    e.preventDefault()
    setFormError('')
    setSuccessMsg('')

    if (date_from > date_to) {
      setFormError('End date must be on or after start date.')
      return
    }

    try {
      const filename = await generateReport({ report_type: reportType, date_from, date_to })
      setSuccessMsg(`Report generated: ${filename}`)
    } catch (err) {
      setFormError(err.message || 'Failed to generate report')
    }
  }

  const columns = [
    { key: 'created_at', header: 'Generated', render: (row) => formatDate(row.created_at) },
    { key: 'type', header: 'Type', render: (row) => row.report_type_label || row.report_type },
    {
      key: 'period',
      header: 'Period',
      render: (row) => `${row.date_from} → ${row.date_to}`,
    },
    {
      key: 'filename',
      header: 'File',
      render: (row) => <code className="text-xs text-zinc-400">{row.filename}</code>,
    },
    {
      key: 'actions',
      header: 'Action',
      render: (row) => (
        <Button variant="ghost" size="sm" onClick={() => downloadReport(row)}>
          Download
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-100">Reports</h1>
        <p className="mt-1 text-sm text-zinc-500">Generate and download incident and compliance reports</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Generate Report</CardTitle>
          <CardDescription>Choose a report type and date range</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleGenerate}>
            <fieldset>
              <legend className="mb-2 text-xs font-medium text-zinc-400">Report type</legend>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {REPORT_TYPES.map((type) => (
                  <label
                    key={type.id}
                    className={cn(
                      'flex cursor-pointer flex-col gap-1 rounded-md border px-3 py-2.5 transition-colors',
                      reportType === type.id
                        ? 'border-amber-500/50 bg-amber-500/5'
                        : 'border-zinc-700 hover:border-zinc-600',
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
                      <span className="text-sm font-medium text-zinc-200">{type.label}</span>
                    </span>
                    <span className="text-xs text-zinc-500">{type.description}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="grid grid-cols-2 gap-3 max-w-md">
              <Input
                label="From"
                type="date"
                value={date_from}
                onChange={(e) => setDateRange((d) => ({ ...d, date_from: e.target.value }))}
                required
              />
              <Input
                label="To"
                type="date"
                value={date_to}
                onChange={(e) => setDateRange((d) => ({ ...d, date_to: e.target.value }))}
                required
              />
            </div>

            {formError ? (
              <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
                {formError}
              </p>
            ) : null}
            {successMsg ? (
              <p className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300" role="status">
                {successMsg}
              </p>
            ) : null}
            {error ? (
              <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
                {error}
              </p>
            ) : null}

            <Button type="submit" variant="primary" disabled={generating}>
              {generating ? 'Generating…' : 'Generate Report'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-zinc-100">Generated Reports</h2>
        <DataTable
          columns={columns}
          data={reports}
          loading={loading}
          emptyTitle="No reports generated yet"
          rowKey={(row) => row.id}
        />
      </div>
    </div>
  )
}
