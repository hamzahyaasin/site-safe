import { useState } from 'react'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'
import Input, { Select } from '../ui/Input.jsx'
import { apiErrorText, useFeedback } from '../../context/FeedbackContext.jsx'
import { cn, formatGas, formatTimestamp } from '../../lib/utils.js'

const emptyForm = { monitor_id: '', name: '', zone: '', latitude: '', longitude: '' }

function toForm(monitor) {
  return {
    monitor_id: monitor.monitor_id,
    name: monitor.name || '',
    zone: monitor.zone ? String(monitor.zone) : '',
    latitude: monitor.latitude ?? '',
    longitude: monitor.longitude ?? '',
  }
}

function toPayload(form) {
  const hasPosition = form.latitude !== '' && form.longitude !== ''
  return {
    monitor_id: form.monitor_id.trim(),
    name: form.name.trim(),
    zone: form.zone ? Number(form.zone) : null,
    latitude: hasPosition ? Number(form.latitude) : null,
    longitude: hasPosition ? Number(form.longitude) : null,
  }
}

/**
 * Fixed gas monitors: each is installed in a zone, and a reading over the
 * limit raises a critical GAS alert for that zone. Readings come only from
 * the devices; Safety Officers and Admins register them and say where they are.
 *
 * ``onPick(fn)`` asks the page's site map for one click, passed to ``fn``
 * as {lat, lng}; ``onPick(null)`` cancels. ``picking`` is true meanwhile.
 */
export default function GasMonitors({ monitors, zones, loading, error, canManage, onCreate, onUpdate, onDelete, onPick, picking }) {
  const { toast, confirm } = useFeedback()
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  function reset() {
    setForm(emptyForm)
    setEditingId(null)
    setFormError('')
    onPick?.(null)
  }

  function edit(monitor) {
    setForm(toForm(monitor))
    setEditingId(monitor.id)
    setFormError('')
  }

  function pickOnMap() {
    onPick?.((point) => setForm((f) => ({ ...f, latitude: point.lat, longitude: point.lng })))
  }

  async function submit(e) {
    e.preventDefault()
    if ((form.latitude === '') !== (form.longitude === '')) {
      setFormError('Give both latitude and longitude, or neither.')
      return
    }
    setSaving(true)
    setFormError('')
    try {
      if (editingId) {
        await onUpdate(editingId, toPayload(form))
        toast(`Gas monitor ${form.monitor_id.trim()} updated`)
      } else {
        await onCreate(toPayload(form))
        toast(`Gas monitor ${form.monitor_id.trim()} registered`)
      }
      reset()
    } catch (err) {
      setFormError(apiErrorText(err))
    } finally {
      setSaving(false)
    }
  }

  async function remove(monitor) {
    const ok = await confirm({
      title: `Remove gas monitor ${monitor.monitor_id}?`,
      message: 'Its readings stop being accepted. Alerts it raised stay in the incident log.',
      confirmLabel: 'Remove monitor',
    })
    if (!ok) return
    try {
      await onDelete(monitor.id)
      if (editingId === monitor.id) reset()
      toast(`Gas monitor ${monitor.monitor_id} removed`)
    } catch (err) {
      toast(apiErrorText(err), 'error')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Gas Monitors</CardTitle>
        <CardDescription>
          Fixed MQ-2 gas monitors installed in zones. A reading of 2,000 ppm or more raises a critical GAS alert for
          the zone. Readings are estimates for spotting a leak, not certified measurements.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? <p className="text-xs text-red-400">{error}</p> : null}
        {loading ? null : monitors.length === 0 ? (
          <p className="text-sm text-zinc-500">No gas monitors registered.</p>
        ) : (
          <ul className="divide-y divide-zinc-800 rounded-md border border-zinc-800">
            {monitors.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-100">
                    <span className="font-mono">{m.monitor_id}</span>
                    {m.name ? <span className="text-zinc-400"> · {m.name}</span> : null}
                    <span className="text-zinc-400"> · {m.zone_name || 'no zone'}</span>
                  </p>
                  <p className="text-xs text-zinc-500">
                    <span className={cn('tabular-nums', m.gas_over_limit ? 'font-semibold text-red-400' : 'text-zinc-300')}>
                      {formatGas(m) || 'no reading yet'}
                    </span>
                    {m.gas_over_limit ? <span className="text-red-400"> — over the alert limit</span> : null}
                    {' · '}last report {m.last_seen ? formatTimestamp(m.last_seen) : 'never'}
                    {m.latitude == null ? ' · not on the map' : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {m.gas_over_limit ? <Badge variant="critical">GAS</Badge> : null}
                  <Badge variant={m.is_online ? 'active' : 'offline'} dot>
                    {m.is_online ? 'Online' : 'Offline'}
                  </Badge>
                  {canManage ? (
                    <>
                      <Button variant="ghost" size="sm" onClick={() => edit(m)}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => remove(m)}>
                        Remove
                      </Button>
                    </>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}

        {canManage ? (
          <form onSubmit={submit} className="grid grid-cols-1 gap-3 md:grid-cols-6 md:items-end">
            <Input
              label="Monitor ID"
              value={form.monitor_id}
              placeholder="GM-01"
              onChange={(e) => setForm({ ...form, monitor_id: e.target.value })}
              required
            />
            <Input
              label="Location name"
              className="md:col-span-2"
              value={form.name}
              placeholder="Basement pump room"
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <Select label="Zone" value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} required>
              <option value="">Choose zone</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </Select>
            <Input
              label="Latitude"
              type="number"
              step="any"
              value={form.latitude}
              onChange={(e) => setForm({ ...form, latitude: e.target.value })}
            />
            <Input
              label="Longitude"
              type="number"
              step="any"
              value={form.longitude}
              onChange={(e) => setForm({ ...form, longitude: e.target.value })}
            />
            <div className="flex flex-wrap items-center gap-3 md:col-span-6">
              <Button type="submit" variant="primary" size="sm" disabled={saving || !form.monitor_id.trim() || !form.zone}>
                {saving ? 'Saving…' : editingId ? 'Save monitor' : 'Register monitor'}
              </Button>
              {onPick ? (
                <Button type="button" variant="secondary" size="sm" onClick={picking ? () => onPick(null) : pickOnMap}>
                  {picking ? 'Cancel map pick' : 'Pick position on map'}
                </Button>
              ) : null}
              {editingId || form.monitor_id ? (
                <Button type="button" variant="ghost" size="sm" onClick={reset}>
                  {editingId ? 'Cancel edit' : 'Clear'}
                </Button>
              ) : null}
              {picking ? <span className="text-xs text-amber-400">Click the site map above to place the monitor.</span> : null}
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
