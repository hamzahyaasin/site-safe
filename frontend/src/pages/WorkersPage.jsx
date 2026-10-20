import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useWorkers } from '../hooks/useWorkers.js'
import { useVests } from '../hooks/useVests.js'
import { useZones } from '../hooks/useZones.js'
import WorkerStatusGrid from '../components/dashboard/WorkerStatusGrid.jsx'
import Button from '../components/ui/Button.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Input, { Select } from '../components/ui/Input.jsx'
import { printBadge } from '../lib/badge.js'
import WorkerTimeline from '../components/workers/WorkerTimeline.jsx'

const EMPTY = { name: '', role: '', phone: '', zone: '', vest: '', is_active: true }

function errorText(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Request failed'
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  return Object.entries(data)
    .map(([field, msgs]) => `${field}: ${[].concat(msgs).join(' ')}`)
    .join(' · ')
}

export default function WorkersPage() {
  const { canOperate, api } = useAuth()
  const { workers, loading, highlightIds, createWorker, updateWorker } = useWorkers()
  const { vests } = useVests({ poll: false })
  const { zones } = useZones()
  const [params, setParams] = useSearchParams()
  const [editing, setEditing] = useState(null) // null = closed, {} = new, worker = edit
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [timelineFor, setTimelineFor] = useState(null)

  // /workers?new=1 (from the dashboard tile) opens the registration form.
  useEffect(() => {
    if (params.get('new') && canOperate) {
      const t = window.setTimeout(() => {
        setForm(EMPTY)
        setError('')
        setEditing({})
        setParams({}, { replace: true })
      }, 0)
      return () => window.clearTimeout(t)
    }
    return undefined
  }, [params, canOperate, setParams])

  function openNew() {
    setForm(EMPTY)
    setError('')
    setEditing({})
  }

  function openEdit(worker) {
    setForm({
      name: worker.name,
      role: worker.role || '',
      phone: worker.phone || '',
      zone: worker.zone ? String(worker.zone) : '',
      vest: worker.smart_vest ? String(worker.smart_vest.id) : '',
      is_active: worker.is_active,
    })
    setError('')
    setEditing(worker)
  }

  // A vest can be chosen if it is free or already this worker's.
  const vestOptions = useMemo(
    () => vests.filter((v) => !v.worker || (editing?.id && v.worker === editing.id)),
    [vests, editing],
  )

  async function save(extra = {}) {
    const body = {
      name: form.name.trim(),
      role: form.role.trim(),
      phone: form.phone.trim(),
      zone: form.zone ? Number(form.zone) : null,
      vest: form.vest ? Number(form.vest) : null,
      ...extra,
    }
    setSaving(true)
    setError('')
    try {
      if (editing?.id) await updateWorker(editing.id, body)
      else await createWorker(body)
      setEditing(null)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setSaving(false)
    }
  }

  async function badgeAction(reissue) {
    if (
      reissue &&
      !window.confirm(`Issue a new badge for ${editing.name}? Every badge printed earlier stops working.`)
    ) {
      return
    }
    setError('')
    try {
      const { data } = reissue
        ? await api.post(`workers/${editing.id}/badge/`)
        : await api.get(`workers/${editing.id}/badge/`)
      await printBadge(data)
    } catch (e) {
      setError(errorText(e))
    }
  }

  const visible = showInactive ? workers : workers.filter((w) => w.is_active)
  const activeCount = workers.filter((w) => w.is_active).length
  const isEdit = Boolean(editing?.id)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Workers</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {activeCount} active · {workers.length - activeCount} deactivated ·{' '}
            {workers.filter((w) => w.is_active && w.smart_vest?.is_online).length} on site by vest
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-zinc-400">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show deactivated
          </label>
          {canOperate ? (
            <Button variant="primary" size="sm" onClick={openNew}>
              Register worker
            </Button>
          ) : null}
        </div>
      </header>

      <WorkerStatusGrid
        workers={visible}
        loading={loading}
        highlightIds={highlightIds}
        onEdit={canOperate ? openEdit : undefined}
        onTimeline={setTimelineFor}
        onAdd={openNew}
        canAdd={canOperate}
      />

      <WorkerTimeline worker={timelineFor} onClose={() => setTimelineFor(null)} />

      <Drawer
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={isEdit ? `Edit ${editing.name}` : 'Register worker'}
        description="Presence is tracked only for workers wearing an assigned vest."
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2">
            {isEdit ? (
              <Button
                variant="ghost"
                size="sm"
                disabled={saving}
                onClick={() => save({ is_active: !editing.is_active })}
              >
                {editing.is_active ? 'Deactivate' : 'Reactivate'}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" disabled={saving || !form.name.trim()} onClick={() => save()}>
                {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Register'}
              </Button>
            </div>
          </div>
        }
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            save()
          }}
        >
          <Input
            label="Full name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            autoFocus
          />
          <Input
            label="Trade / role"
            value={form.role}
            placeholder="e.g. Electrician"
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          />
          <Input
            label="Phone"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          <Select
            label="Assigned zone"
            value={form.zone}
            onChange={(e) => setForm({ ...form, zone: e.target.value })}
          >
            <option value="">None</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name} ({z.risk_level.toLowerCase()})
              </option>
            ))}
          </Select>
          <Select
            label="Smart vest"
            value={form.vest}
            onChange={(e) => setForm({ ...form, vest: e.target.value })}
          >
            <option value="">No vest</option>
            {vestOptions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.vest_id}
              </option>
            ))}
          </Select>
          {isEdit && editing.is_active ? (
            <div className="rounded-md border border-zinc-800 p-3">
              <p className="text-xs font-medium text-zinc-300">QR identity badge</p>
              <p className="mt-1 text-[11px] text-zinc-500">
                Cameras attribute alerts to this worker when the badge is readable on them.
              </p>
              <div className="mt-2 flex gap-2">
                <Button type="button" variant="secondary" size="sm" onClick={() => badgeAction(false)}>
                  Print badge
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => badgeAction(true)}>
                  Reissue badge
                </Button>
              </div>
            </div>
          ) : null}
          <p className="text-[11px] text-zinc-500">
            Only unassigned vests are listed. Register new vests on the Vest Management page.
            Deactivating a worker releases their vest and keeps their incident history.
          </p>
          {error ? (
            <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" hidden />
        </form>
      </Drawer>
    </div>
  )
}
