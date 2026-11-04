import { useState } from 'react'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Alert from '../components/ui/Alert.jsx'
import Input, { Checkbox, Select, Textarea } from '../components/ui/Input.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { IconPencil, IconPlus, IconTrash } from '../components/ui/icons.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'
import CameraPlacementPanel from '../components/map/CameraPlacementPanel.jsx'
import SiteMap from '../components/map/SiteMap.jsx'
import HotWorkPermits from '../components/zones/HotWorkPermits.jsx'
import { useHotWorkPermits } from '../hooks/useHotWorkPermits.js'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import { useCameraMap } from '../hooks/useCameraMap.js'
import { useZones } from '../hooks/useZones.js'
import { useVests } from '../hooks/useVests.js'
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
  boundaries: [],
  camera_ids: '',
  camera_views_overlap: true,
  is_active: true,
}

function formatOccupancy(zone) {
  const present = zone.current_occupancy ?? 0
  return zone.max_occupancy ? `${present} / ${zone.max_occupancy}` : `${present} / ∞`
}

/** How the head count was reached, e.g. "cameras 3 (largest of 2) · 2 identified". */
function occupancyBasis(zone) {
  const o = zone.occupancy
  if (!o) return null
  const parts = []
  if (o.camera_count !== null) {
    const how = o.cameras_reporting > 1 ? ` (${o.method === 'max' ? 'largest' : 'sum'} of ${o.cameras_reporting})` : ''
    parts.push(`cameras ${o.camera_count}${how}`)
  } else if (o.cameras_assigned) {
    parts.push('no camera reporting')
  }
  parts.push(`${o.identified} identified`)
  return parts.join(' · ')
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
    boundaries: zone.boundaries ?? [],
    camera_ids: (zone.camera_ids ?? []).join(', '),
    camera_views_overlap: zone.camera_views_overlap ?? true,
    is_active: zone.is_active ?? true,
  }
}

export default function ZonesPage() {
  const { zones, loading, error, createZone, updateZone, deleteZone } = useZones()
  const { vests } = useVests()
  const cameraMap = useCameraMap()
  const [cameraDraft, setCameraDraft] = useState(null)
  // Zone edits are Admin-only server-side; hide the controls for everyone else.
  const { isAdmin, canOperate } = useAuth()
  const { toast, confirm } = useFeedback()
  const permitState = useHotWorkPermits()
  const activePermitZones = new Set(permitState.permits.filter((p) => p.is_active).map((p) => p.zone))
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
      const boundaries = form.boundaries
      if (boundaries.length > 0 && boundaries.length < 3) {
        throw new Error('A boundary needs at least three points (or none for a camera-only zone).')
      }
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        risk_level: form.risk_level,
        max_occupancy: Number(form.max_occupancy) || 0,
        boundaries,
        camera_ids: parseCameraIds(form.camera_ids),
        camera_views_overlap: form.camera_views_overlap,
        is_active: form.is_active,
      }
      if (editingZone) {
        await updateZone(editingZone.id, payload)
        toast(`Zone "${payload.name}" saved`)
      } else {
        await createZone(payload)
        toast(`Zone "${payload.name}" created`)
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
    const ok = await confirm({
      title: `Delete zone "${zone.name}"?`,
      message:
        'Workers assigned to it are unlinked, and its boundary, zone-specific alert rules and hot-work permits are removed. Past incidents are kept.',
      confirmLabel: 'Delete zone',
    })
    if (!ok) return
    try {
      await deleteZone(zone.id)
      toast(`Zone "${zone.name}" deleted`)
    } catch (err) {
      toast(apiErrorText(err, 'Failed to delete zone'), 'error')
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (row) => (
        <div>
          <p className="whitespace-nowrap font-medium text-zinc-100">{row.name}</p>
          {row.description ? <p className="mt-0.5 text-xs text-zinc-500">{row.description}</p> : null}
        </div>
      ),
    },
    {
      key: 'risk_level',
      header: 'Risk Level',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          <Badge variant={RISK_BADGE[row.risk_level] || 'neutral'}>{row.risk_level}</Badge>
          {activePermitZones.has(row.id) ? <Badge variant="high">HOT WORK</Badge> : null}
        </div>
      ),
    },
    {
      key: 'workers',
      header: 'Assigned',
      render: (row) => row.worker_count ?? 0,
    },
    {
      key: 'occupancy',
      header: 'Present / Max',
      render: (row) =>
        row.boundaries?.length >= 3 || row.camera_ids?.length ? (
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-zinc-200">{formatOccupancy(row)}</span>
              {row.capacity_alerted_at ? <Badge variant="critical">Over capacity</Badge> : null}
            </div>
            <div className="text-[11px] text-zinc-500">{occupancyBasis(row)}</div>
          </div>
        ) : (
          <span className="text-zinc-600" title="People are counted by the zone's cameras and by vest GPS inside its boundary">
            no boundary or camera
          </span>
        ),
    },
    {
      key: 'cameras',
      header: 'Cameras',
      render: (row) =>
        row.camera_ids?.length ? (
          <div>
            <span className="font-mono text-xs text-zinc-400">{row.camera_ids.join(', ')}</span>
            {row.camera_ids.length > 1 ? (
              <div className="text-[11px] text-zinc-500">
                {row.camera_views_overlap ? 'Views overlap' : 'Separate views'}
              </div>
            ) : null}
          </div>
        ) : (
          <span className="text-zinc-600">None assigned</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge variant={row.is_active ? 'active' : 'offline'} dot>
          {row.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
  ]

  if (isAdmin) {
    columns.push({
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      cellClassName: 'text-right',
      render: (row) => (
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="xs" onClick={() => openEdit(row)}>
            <IconPencil className="h-3.5 w-3.5" />
            Edit
          </Button>
          <Button variant="danger" size="xs" onClick={() => handleDelete(row)} aria-label={`Delete zone ${row.name}`}>
            <IconTrash className="h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      ),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Zones"
        description={
          isAdmin
            ? 'Manage site zones, risk levels, geofence boundaries and camera placement'
            : 'Site zones, risk levels, and geofence boundaries (read-only)'
        }
        actions={
          isAdmin ? (
            <Button variant="primary" size="sm" onClick={openCreate}>
              <IconPlus className="h-3.5 w-3.5" />
              Add zone
            </Button>
          ) : null
        }
      />

      {error ? <Alert>{error}</Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle>Site Map</CardTitle>
          <CardDescription>
            Zone boundaries by risk level, vest positions and camera coverage. Click the map to zoom with the wheel.
          </CardDescription>
          <MapLegend />
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <SiteMap
            zones={zones}
            vests={vests}
            cameras={cameraMap.cameras}
            alerting={cameraMap.alerting}
            cameraDraft={cameraDraft}
            onAddPoint={cameraDraft ? ({ lat, lng }) => setCameraDraft((d) => ({ ...d, latitude: lat, longitude: lng })) : undefined}
            height={380}
          />
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Cameras</p>
            {cameraMap.error ? <p className="mb-2 text-xs text-red-400">{cameraMap.error}</p> : null}
            <CameraPlacementPanel
              cameras={cameraMap.cameras}
              alerting={cameraMap.alerting}
              draft={cameraDraft}
              setDraft={setCameraDraft}
              place={cameraMap.place}
              unplace={cameraMap.unplace}
              isAdmin={isAdmin}
            />
          </div>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-100">All zones</h2>
        <DataTable
          columns={columns}
          data={zones}
          loading={loading}
          emptyTitle="No zones yet"
          emptyDescription={isAdmin ? 'Add one with the Add zone button above.' : 'An admin has not defined any zones yet.'}
          rowKey={(row) => row.id}
        />
      </section>

      <HotWorkPermits
        zones={zones}
        permits={permitState.permits}
        loading={permitState.loading}
        error={permitState.error}
        canIssue={canOperate}
        onIssue={permitState.issue}
        onRevoke={permitState.revoke}
      />

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        size="lg"
        title={editingZone ? `Edit ${editingZone.name}` : 'Add zone'}
        description={editingZone ? 'Update zone details and geofence boundaries' : 'Define a new site zone'}
        footer={
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={closeDrawer} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" form="zone-form" variant="primary" loading={saving}>
              {editingZone ? 'Save changes' : 'Create zone'}
            </Button>
          </div>
        }
      >
        <form id="zone-form" className="space-y-4" onSubmit={handleSubmit}>
          {formError ? <Alert>{formError}</Alert> : null}

          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />

          <Textarea
            label="Description"
            rows={2}
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />

          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Risk level"
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
              label="Max occupancy"
              type="number"
              min={0}
              value={form.max_occupancy}
              onChange={(e) => setForm((f) => ({ ...f, max_occupancy: e.target.value }))}
              hint="0 = unlimited"
            />
          </div>

          <Input
            label="Camera IDs"
            value={form.camera_ids}
            onChange={(e) => setForm((f) => ({ ...f, camera_ids: e.target.value }))}
            placeholder="CAM-ENTRANCE, CAM-BAY-2"
            hint={
              <>
                Comma-separated, matching the <code className="font-mono">--camera-id</code> each vision pipeline is
                started with. A camera belongs to one zone: a badge it reads places that worker here.
              </>
            }
          />

          <Checkbox
            label="These cameras can see the same people"
            hint="On: the head count is the largest single camera count, so nobody is counted twice. Off: the cameras watch separate areas and their counts are added."
            checked={form.camera_views_overlap}
            onChange={(e) => setForm((f) => ({ ...f, camera_views_overlap: e.target.checked }))}
          />

          {editingZone ? (
            <Checkbox
              label="Active"
              hint="Inactive zones keep their history but raise no alerts."
              checked={form.is_active}
              onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
          ) : null}

          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-zinc-300">Boundary</span>
            <SiteMap
              zones={zones}
              vests={vests}
              excludeZoneId={editingZone?.id}
              draft={form.boundaries}
              onAddPoint={(p) => setForm((f) => ({ ...f, boundaries: [...f.boundaries, p] }))}
              height={280}
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] text-zinc-500">
                Click the map to add corners in order · {form.boundaries.length} point
                {form.boundaries.length === 1 ? '' : 's'}
                {form.boundaries.length > 0 && form.boundaries.length < 3 ? ' (need at least 3)' : ''}
              </span>
              <div className="flex gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={form.boundaries.length === 0}
                  onClick={() => setForm((f) => ({ ...f, boundaries: f.boundaries.slice(0, -1) }))}
                >
                  Undo point
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={form.boundaries.length === 0}
                  onClick={() => setForm((f) => ({ ...f, boundaries: [] }))}
                >
                  Clear
                </Button>
              </div>
            </div>
            <span className="text-[11px] text-zinc-500">
              Leave empty for a camera-only zone. GPS presence, restricted-entry and capacity alerts need a boundary.
            </span>
          </div>
        </form>
      </Drawer>
    </div>
  )
}

const LEGEND = [
  { label: 'Low', color: '#3b82f6' },
  { label: 'Medium', color: '#eab308' },
  { label: 'High', color: '#f97316' },
  { label: 'Restricted', color: '#ef4444' },
]

function MapLegend() {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-400">
      {LEGEND.map((l) => (
        <span key={l.label} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border" style={{ borderColor: l.color, background: `${l.color}33` }} />
          {l.label} risk
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-emerald-500" /> Vest online / camera live
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-zinc-500" /> Offline
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-red-500" /> SOS / alerting
      </span>
    </div>
  )
}
