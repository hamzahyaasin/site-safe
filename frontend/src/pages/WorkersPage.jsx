import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useWorkers } from '../hooks/useWorkers.js'
import { useVests } from '../hooks/useVests.js'
import { useZones } from '../hooks/useZones.js'
import WorkerStatusGrid from '../components/dashboard/WorkerStatusGrid.jsx'
import Alert from '../components/ui/Alert.jsx'
import Button from '../components/ui/Button.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Input, { Checkbox, Select } from '../components/ui/Input.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { IconPlus } from '../components/ui/icons.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'
import { printBadge } from '../lib/badge.js'
import { getWorkerPresence } from '../lib/utils.js'
import WorkerTimeline from '../components/workers/WorkerTimeline.jsx'

const EMPTY = { name: '', role: '', phone: '', zone: '', vest: '', is_active: true }

const errorText = (err) => apiErrorText(err, 'Request failed')

export default function WorkersPage() {
  const { canOperate, api } = useAuth()
  const { toast, confirm } = useFeedback()
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
      toast(
        extra.is_active === false
          ? `${body.name} deactivated`
          : extra.is_active === true
            ? `${body.name} reactivated`
            : editing?.id
              ? 'Worker updated'
              : `${body.name} registered`,
      )
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
      !(await confirm({
        title: `Reissue ${editing.name}'s badge?`,
        message: 'A new QR code is issued and every badge printed earlier stops working. Print and hand out the new one.',
        confirmLabel: 'Reissue badge',
      }))
    ) {
      return
    }
    setError('')
    try {
      const { data } = reissue
        ? await api.post(`workers/${editing.id}/badge/`)
        : await api.get(`workers/${editing.id}/badge/`)
      await printBadge(data)
      if (reissue) toast('New badge issued — the print dialog has opened')
    } catch (e) {
      setError(errorText(e))
    }
  }

  const visible = showInactive ? workers : workers.filter((w) => w.is_active)
  const activeCount = workers.filter((w) => w.is_active).length
  const isEdit = Boolean(editing?.id)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workers"
        description={`${activeCount} active · ${workers.length - activeCount} deactivated · ${
          workers.filter((w) => w.is_active && getWorkerPresence(w).label === 'ON SITE').length
        } on site`}
        actions={
          <>
            <Checkbox
              label="Show deactivated"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="mr-2 text-xs text-zinc-300"
            />
            {canOperate ? (
              <Button variant="primary" size="sm" onClick={openNew}>
                <IconPlus className="h-3.5 w-3.5" />
                Register worker
              </Button>
            ) : null}
          </>
        }
      />

      <WorkerStatusGrid
        title="All workers"
        description="Presence from camera badge sightings and vest GPS. Open a timeline for a worker's movements."
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
                variant={editing.is_active ? 'danger' : 'secondary'}
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
              <Button variant="ghost" size="sm" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" loading={saving} disabled={!form.name.trim()} onClick={() => save()}>
                {isEdit ? 'Save changes' : 'Register worker'}
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
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3.5">
              <p className="text-sm font-medium text-zinc-200">QR identity badge</p>
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
          {error ? <Alert>{error}</Alert> : null}
          <button type="submit" hidden />
        </form>
      </Drawer>
    </div>
  )
}
