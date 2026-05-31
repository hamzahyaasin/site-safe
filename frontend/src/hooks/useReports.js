import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeList(data) {
  return Array.isArray(data) ? data : data?.results || []
}

function parseFilename(contentDisposition) {
  if (!contentDisposition) return null
  const match = /filename="?([^";\n]+)"?/.exec(contentDisposition)
  return match ? match[1] : null
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function useReports() {
  const { api } = useAuth()
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get('v1/reports/')
      setReports(normalizeList(data))
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load reports')
      setReports([])
    } finally {
      setLoading(false)
    }
  }, [api])

  const generateReport = useCallback(
    async ({ report_type, date_from, date_to }) => {
      setGenerating(true)
      setError(null)
      try {
        const response = await api.post(
          'v1/reports/generate/',
          { report_type, date_from, date_to },
          { responseType: 'blob' },
        )
        const filename =
          parseFilename(response.headers['content-disposition']) ||
          `${report_type.toLowerCase()}_report.docx`
        downloadBlob(response.data, filename)
        await loadReports()
        return filename
      } catch (e) {
        let message = e.message || 'Failed to generate report'
        if (e.response?.data instanceof Blob) {
          const text = await e.response.data.text()
          try {
            const parsed = JSON.parse(text)
            message = parsed.detail || message
          } catch {
            if (text) message = text
          }
        } else if (e.response?.data?.detail) {
          message = e.response.data.detail
        }
        throw new Error(message)
      } finally {
        setGenerating(false)
      }
    },
    [api, loadReports],
  )

  const downloadReport = useCallback(
    async (report) => {
      const response = await api.get(`v1/reports/${report.id}/download/`, {
        responseType: 'blob',
      })
      const filename =
        parseFilename(response.headers['content-disposition']) ||
        report.filename ||
        `report_${report.id}.docx`
      downloadBlob(response.data, filename)
    },
    [api],
  )

  useEffect(() => {
    loadReports()
  }, [loadReports])

  return {
    reports,
    loading,
    generating,
    error,
    loadReports,
    generateReport,
    downloadReport,
  }
}
