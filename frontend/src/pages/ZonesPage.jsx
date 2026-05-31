import { useState } from 'react'
import { useZones } from '../hooks/useZones.js'

const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'RESTRICTED']

const emptyForm = {
  name: '',
  description: '',
  risk_level: 'MEDIUM',
  max_occupancy: 0,
  boundaries: '[]',
  is_active: true,
}

function riskBadgeClass(level) {
  switch (level) {
    case 'LOW':
      return 'badge badge--low'
    case 'MEDIUM':
      return 'badge badge--medium'
    case 'HIGH':
      return 'badge badge--high'
    case 'RESTRICTED':
      return 'badge badge--critical'
    default:
      return 'badge'
  }
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
    throw new Error(e.message || 'Invalid boundaries JSON')
  }
}

function zoneToForm(zone) {
  return {
    name: zone.name || '',
    description: zone.description || '',
    risk_level: zone.risk_level || 'MEDIUM',
    max_occupancy: zone.max_occupancy ?? 0,
    boundaries: JSON.stringify(zone.boundaries ?? [], null, 2),
    is_active: zone.is_active ?? true,
  }
}

export default function ZonesPage() {
  const { zones, loading, error, createZone, updateZone, deleteZone } = useZones()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingZone, setEditingZone] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  function openCreate() {
    setEditingZone(null)
    setForm(emptyForm)
    setFormError('')
    setModalOpen(true)
  }

  function openEdit(zone) {
    setEditingZone(zone)
    setForm(zoneToForm(zone))
    setFormError('')
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
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
        is_active: form.is_active,
      }
      if (editingZone) {
        await updateZone(editingZone.id, payload)
      } else {
        await createZone(payload)
      }
      closeModal()
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

  return (
    <div className="page zones-page">
      <header className="page-header page-header--split">
        <div>
          <h1 className="page__title">Zones</h1>
          <p className="page__lead">Manage site zones, risk levels, and geofence boundaries</p>
        </div>
        <button type="button" className="btn btn--primary" onClick={openCreate}>
          Add Zone
        </button>
      </header>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Risk Level</th>
              <th>Workers</th>
              <th>Max Occupancy</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  Loading zones…
                </td>
              </tr>
            ) : zones.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  No zones yet. Add one with the button above.
                </td>
              </tr>
            ) : (
              zones.map((zone) => (
                <tr key={zone.id}>
                  <td>
                    <div className="zone-name-cell">
                      <strong>{zone.name}</strong>
                      {zone.description ? (
                        <span className="zone-desc">{zone.description}</span>
                      ) : null}
                    </div>
                  </td>
                  <td>
                    <span className={riskBadgeClass(zone.risk_level)}>{zone.risk_level}</span>
                  </td>
                  <td>{zone.worker_count ?? zone.current_occupancy ?? 0}</td>
                  <td>{formatOccupancy(zone)}</td>
                  <td>
                    <span className={zone.is_active ? 'badge badge--low' : 'badge badge--medium'}>
                      {zone.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="actions-cell">
                    <button type="button" className="btn btn--sm btn--ghost" onClick={() => openEdit(zone)}>
                      Edit
                    </button>
                    <button type="button" className="btn btn--sm btn--danger" onClick={() => handleDelete(zone)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modalOpen ? (
        <div className="modal-backdrop" role="presentation" onClick={closeModal}>
          <div
            className="modal-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="zone-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="modal-panel__header">
              <h2 id="zone-modal-title" className="modal-panel__title">
                {editingZone ? 'Edit Zone' : 'Add Zone'}
              </h2>
              <button type="button" className="btn btn--ghost btn--sm" onClick={closeModal} aria-label="Close">
                ✕
              </button>
            </header>

            <form className="modal-panel__form" onSubmit={handleSubmit}>
              {formError ? (
                <p className="form-error" role="alert">
                  {formError}
                </p>
              ) : null}

              <label className="field">
                <span className="field__label">Name</span>
                <input
                  className="field__input"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                />
              </label>

              <label className="field">
                <span className="field__label">Description</span>
                <textarea
                  className="field__input field__textarea"
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                />
              </label>

              <div className="inline-form__grid">
                <label className="field">
                  <span className="field__label">Risk Level</span>
                  <select
                    className="field__select"
                    value={form.risk_level}
                    onChange={(e) => setForm((f) => ({ ...f, risk_level: e.target.value }))}
                  >
                    {RISK_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="field__label">Max Occupancy</span>
                  <input
                    className="field__input"
                    type="number"
                    min={0}
                    value={form.max_occupancy}
                    onChange={(e) => setForm((f) => ({ ...f, max_occupancy: e.target.value }))}
                  />
                  <span className="field__hint">0 = unlimited</span>
                </label>
              </div>

              {editingZone ? (
                <label className="field field--checkbox">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  />
                  <span>Active</span>
                </label>
              ) : null}

              <label className="field">
                <span className="field__label">Boundaries (JSON polygon)</span>
                <textarea
                  className="field__input field__textarea field__textarea--mono"
                  rows={6}
                  value={form.boundaries}
                  onChange={(e) => setForm((f) => ({ ...f, boundaries: e.target.value }))}
                  placeholder='[{"lat": 33.6844, "lng": 73.0479}, ...]'
                />
                <span className="field__hint">Array of {`{lat, lng}`} vertices (min 3 for geofencing)</span>
              </label>

              <div className="modal-panel__actions">
                <button type="submit" className="btn btn--primary" disabled={saving}>
                  {saving ? 'Saving…' : editingZone ? 'Save changes' : 'Create zone'}
                </button>
                <button type="button" className="btn btn--ghost" onClick={closeModal} disabled={saving}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
