import { useState } from 'react'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Input, { Select } from '../ui/Input.jsx'
import { formatDateTime } from '../../lib/utils.js'
import { useFeedback } from '../../context/FeedbackContext.jsx'

function localInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function errorText(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Request failed'
  if (data.detail) return data.detail
  return Object.entries(data)
    .map(([k, v]) => `${k}: ${[].concat(v).join(' ')}`)
    .join(' · ')
}

/**
 * Hot-work permits: fire or smoke seen in a permitted zone during the permit
 * window is still alerted, at reduced severity and linked to the permit.
 */
export default function HotWorkPermits({ zones, permits, loading, error, canIssue, onIssue, onRevoke }) {
  const { toast, confirm } = useFeedback()
  const now = new Date()
  const [form, setForm] = useState(() => ({
    zone: '',
    description: '',
    starts_at: localInputValue(now),
    ends_at: localInputValue(new Date(now.getTime() + 4 * 3600 * 1000)),
  }))
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await onIssue({
        zone: Number(form.zone),
        description: form.description.trim(),
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      })
      setForm((f) => ({ ...f, description: '' }))
    } catch (err) {
      setFormError(errorText(err))
    } finally {
      setSaving(false)
    }
  }

  async function revoke(permit) {
    const ok = await confirm({
      title: `Revoke the hot-work permit for ${permit.zone_name}?`,
      message: 'Fire or smoke seen in this zone becomes a critical alert again.',
      confirmLabel: 'Revoke permit',
    })
    if (!ok) return
    try {
      await onRevoke(permit.id)
      toast('Permit revoked')
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hot-Work Permits</CardTitle>
        <CardDescription>
          Fire or smoke seen in a zone with an active permit is still recorded and shown, at lower severity
          and linked to the permit. Outside a permit it is critical. Permits never hide fire.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? <p className="text-xs text-red-400">{error}</p> : null}
        {loading ? null : permits.length === 0 ? (
          <p className="text-sm text-zinc-500">No active or upcoming permits.</p>
        ) : (
          <ul className="divide-y divide-zinc-800 rounded-md border border-zinc-800">
            {permits.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-100">
                    {p.zone_name} — {p.description}
                  </p>
                  <p className="text-xs text-zinc-500">
                    {formatDateTime(p.starts_at)} → {formatDateTime(p.ends_at)}
                    {p.issued_by_email ? ` · issued by ${p.issued_by_email}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={p.is_active ? 'high' : 'neutral'}>{p.is_active ? 'ACTIVE' : 'UPCOMING'}</Badge>
                  {canIssue ? (
                    <Button variant="ghost" size="sm" onClick={() => revoke(p)}>
                      Revoke
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}

        {canIssue ? (
          <form onSubmit={submit} className="grid grid-cols-1 gap-3 md:grid-cols-5 md:items-end">
            <Select label="Zone" value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} required>
              <option value="">Choose zone</option>
              {zones
                .filter((z) => z.is_active)
                .map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
            </Select>
            <Input
              label="Work"
              className="md:col-span-2"
              value={form.description}
              placeholder="Welding level 3 beams"
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
            <Input
              label="From"
              type="datetime-local"
              value={form.starts_at}
              onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
              required
            />
            <Input
              label="Until (max 12 h)"
              type="datetime-local"
              value={form.ends_at}
              onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
              required
            />
            <div className="md:col-span-5 flex items-center gap-3">
              <Button type="submit" variant="primary" size="sm" disabled={saving || !form.zone || !form.description.trim()}>
                {saving ? 'Issuing…' : 'Issue permit'}
              </Button>
              {formError ? (
                <span className="text-xs text-red-400" role="alert">
                  {formError}
                </span>
              ) : null}
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  )
}
