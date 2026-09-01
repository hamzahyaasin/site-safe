import { useState } from 'react'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Input, { Select } from '../components/ui/Input.jsx'
import { useZones } from '../hooks/useZones.js'
import { useAuth } from '../context/AuthContext.jsx'

const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'RESTRICTED']

const RISK_BADGE = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  RESTRICTED: 'critical',
}

const emptyForm = {
  name: '',
  description: '',
  risk_level: 'MEDIUM',
  max_occupancy: 0,
  boundaries: '[]',
  camera_ids: '',
  is_active: true,
}

function formatOccupancy(zone) {
  const count = zone.worker_count ?? zone.current_occupancy ?? 0
  if (!zone.max_occupancy) return `${count} / ∞`
  return `${count} / ${zone.max_occupancy}`
}

function parseBoundaries(raw) {
  try {
    const parsed = JSON.parse(raw || '[]')
    if (!Array.isArray(parsed)) {
      throw new Error('Boundaries must be a JSON array')
    }
    return parsed
  } catch (e) {
    throw new Error(e.message || 'Invalid boundaries JSON', { cause: e })
  }
}

function parseCameraIds(raw) {
  return raw
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)
}

function zoneToForm(zone) {
  return {
    name: zone.name || '',
    description: zone.description || '',
    risk_level: zone.risk_level || 'MEDIUM',
    max_occupancy: zone.max_occupancy ?? 0,
    boundaries: JSON.stringify(zone.boundaries ?? [], null, 2),
    camera_ids: (zone.camera_ids ?? []).join(', '),
    is_active: zone.is_active ?? true,
  }
}

const textareaClass =
  'rounded-md border border-zinc-700 bg-zinc-900/80 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30'

export default function ZonesPage() {
  const { zones, loading, error, createZone, updateZone, deleteZone } = useZones()
  // Zone edits are Admin-only server-side; hide the controls for everyone else.
  const { isAdmin } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingZone, setEditingZone] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  function openCreate() {
    setEditingZone(null)
    setForm(emptyForm)
    setFormError('')
    setDrawerOpen(true)
  }

  function openEdit(zone) {
    setEditingZone(zone)
    setForm(zoneToForm(zone))
    setFormError('')
    setDrawerOpen(true)
  }

  function closeDrawer() {
    setDrawerOpen(false)
    setEditingZone(null)
    setForm(emptyForm)
    setFormError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      const boundaries = parseBoundaries(form.boundaries)
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        risk_level: form.risk_level,
        max_occupancy: Number(form.max_occupancy) || 0,
        boundaries,
        camera_ids: parseCameraIds(form.camera_ids),
        is_active: form.is_active,
      }
      if (editingZone) {
        await updateZone(editingZone.id, payload)
      } else {
        await createZone(payload)
      }
      closeDrawer()
    } catch (err) {
      const detail = err.response?.data
      if (typeof detail === 'object' && detail !== null) {
        const msg = Object.entries(detail)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('; ')
        setFormError(msg || 'Failed to save zone')
      } else {
        setFormError(err.message || detail || 'Failed to save zone')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(zone) {
    const ok = window.confirm(`Delete zone "${zone.name}"? Workers assigned to this zone will be unlinked.`)
    if (!ok) return
    try {
      await deleteZone(zone.id)
    } catch (err) {
      window.alert(err.response?.data?.detail || 'Failed to delete zone')
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (row) => (
        <div>
          <p className="font-medium text-zinc-100">{row.name}</p>
          {row.description ? <p className="mt-0.5 text-xs text-zinc-500">{row.description}</p> : null}
        </div>
      ),
    },
    {
      key: 'risk_level',
      header: 'Risk Level',
      render: (row) => <Badge variant={RISK_BADGE[row.risk_level] || 'neutral'}>{row.risk_level}</Badge>,
    },
    {
      key: 'workers',
      header: 'Workers',
      render: (row) => row.worker_count ?? row.current_occupancy ?? 0,
    },
    {
      key: 'occupancy',
      header: 'Max Occupancy',
      render: (row) => formatOccupancy(row),
    },
    {
      key: 'cameras',
      header: 'Cameras',
      render: (row) =>
        row.camera_ids?.length ? (
          <span className="font-mono text-xs text-zinc-400">{row.camera_ids.join(', ')}</span>
        ) : (
          <span className="text-zinc-600">None assigned</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge variant={row.is_active ? 'active' : 'offline'}>{row.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
  ]

  if (isAdmin) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
            Edit
          </Button>
          <Button variant="destructive" size="sm" onClick={() => handleDelete(row)}>
            Delete
          </Button>
        </div>
      ),
    })
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Zones</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {isAdmin
              ? 'Manage site zones, risk levels, and geofence boundaries'
              : 'Site zones, risk levels, and geofence boundaries (read-only)'}
          </p>
        </div>
        {isAdmin ? (
          <Button variant="primary" size="sm" onClick={openCreate}>
            Add Zone
          </Button>
        ) : null}
      </header>

      {error ? (
        <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      <DataTable
        columns={columns}
        data={zones}
        loading={loading}
        emptyTitle="No zones yet"
        emptyDescription="Add one with the button above."
        rowKey={(row) => row.id}
      />

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={editingZone ? 'Edit Zone' : 'Add Zone'}
        description={editingZone ? 'Update zone details and geofence boundaries' : 'Define a new site zone'}
        footer={
          <div className="flex gap-2">
            <Button type="submit" form="zone-form" variant="primary" disabled={saving}>
              {saving ? 'Saving…' : editingZone ? 'Save changes' : 'Create zone'}
            </Button>
            <Button type="button" variant="ghost" onClick={closeDrawer} disabled={saving}>
              Cancel
            </Button>
          </div>
        }
      >
        <form id="zone-form" className="space-y-4" onSubmit={handleSubmit}>
          {formError ? (
            <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
              {formError}
            </p>
          ) : null}

          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-zinc-400">Description</span>
            <textarea
              className={textareaClass}
              rows={2}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Risk Level"
              value={form.risk_level}
              onChange={(e) => setForm((f) => ({ ...f, risk_level: e.target.value }))}
            >
              {RISK_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </Select>

            <Input
              label="Max Occupancy"
              type="number"
              min={0}
              value={form.max_occupancy}
              onChange={(e) => setForm((f) => ({ ...f, max_occupancy: e.target.value }))}
            />
          </div>
          <p className="-mt-2 text-xs text-zinc-600">0 = unlimited</p>

          <Input
            label="Camera IDs"
            value={form.camera_ids}
            onChange={(e) => setForm((f) => ({ ...f, camera_ids: e.target.value }))}
            placeholder="CAM-ENTRANCE, CAM-BAY-2"
          />
          <p className="-mt-2 text-[11px] text-zinc-600">
            Comma-separated camera identifiers assigned to watch this zone — match the{' '}
            <code className="font-mono">--camera-id</code> each vision pipeline instance is started with.
          </p>

          {editingZone ? (
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              Active
            </label>
          ) : null}

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-zinc-400">Boundaries (JSON polygon)</span>
            <textarea
              className={`${textareaClass} font-mono`}
              rows={6}
              value={form.boundaries}
              onChange={(e) => setForm((f) => ({ ...f, boundaries: e.target.value }))}
              placeholder='[{"lat": 33.6844, "lng": 73.0479}, ...]'
            />
            <span className="text-[11px] text-zinc-600">Array of {'{lat, lng}'} vertices (min 3 for geofencing)</span>
          </label>
        </form>
      </Drawer>
    </div>
  )
}
