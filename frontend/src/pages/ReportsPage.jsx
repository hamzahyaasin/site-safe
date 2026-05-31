import { useState } from 'react'
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

  return (
    <div className="page reports-page">
      <header className="page-header">
        <div>
          <h1 className="page__title">Reports</h1>
          <p className="page__lead">Generate and download incident and compliance reports</p>
        </div>
      </header>

      <section className="report-generator">
        <h2 className="inline-form__title">Generate Report</h2>

        <form className="report-generator__form" onSubmit={handleGenerate}>
          <fieldset className="report-type-group">
            <legend className="field__label">Report type</legend>
            <div className="report-type-options">
              {REPORT_TYPES.map((type) => (
                <label
                  key={type.id}
                  className={`report-type-option ${reportType === type.id ? 'report-type-option--active' : ''}`}
                >
                  <input
                    type="radio"
                    name="report_type"
                    value={type.id}
                    checked={reportType === type.id}
                    onChange={() => setReportType(type.id)}
                  />
                  <span className="report-type-option__title">{type.label}</span>
                  <span className="report-type-option__desc">{type.description}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="inline-form__grid">
            <label className="field">
              <span className="field__label">From</span>
              <input
                className="field__input"
                type="date"
                value={date_from}
                onChange={(e) => setDateRange((d) => ({ ...d, date_from: e.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">To</span>
              <input
                className="field__input"
                type="date"
                value={date_to}
                onChange={(e) => setDateRange((d) => ({ ...d, date_to: e.target.value }))}
                required
              />
            </label>
          </div>

          {formError ? (
            <p className="form-error" role="alert">
              {formError}
            </p>
          ) : null}
          {successMsg ? (
            <p className="form-success" role="status">
              {successMsg}
            </p>
          ) : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}

          <div className="inline-form__actions">
            <button type="submit" className="btn btn--primary" disabled={generating}>
              {generating ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
        </form>
      </section>

      <section className="report-history">
        <h2 className="inline-form__title">Generated Reports</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Generated</th>
                <th>Type</th>
                <th>Period</th>
                <th>File</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="empty-cell">
                    Loading reports…
                  </td>
                </tr>
              ) : reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-cell">
                    No reports generated yet.
                  </td>
                </tr>
              ) : (
                reports.map((report) => (
                  <tr key={report.id}>
                    <td>{formatDate(report.created_at)}</td>
                    <td>{report.report_type_label || report.report_type}</td>
                    <td>
                      {report.date_from} → {report.date_to}
                    </td>
                    <td>
                      <code>{report.filename}</code>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        onClick={() => downloadReport(report)}
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
