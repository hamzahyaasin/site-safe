import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

const emptyForm = { name: '', vest_id: '', zone: '' }

function initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function IconPlus() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function IconMapPin() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  )
}

export default function WorkersPage() {
  const { api } = useAuth()
  const [workers, setWorkers] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState(emptyForm)
  const [deletingId, setDeletingId] = useState(null)

  const loadWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(Array.isArray(data) ? data : data.results || [])
  }, [api])

  useEffect(() => { loadWorkers() }, [loadWorkers])

  async function handleCreate(e) {
    e.preventDefault()
    await api.post('workers/', { name: form.name, vest_id: form.vest_id, zone: form.zone, is_active: true })
    setForm(emptyForm)
    setShowAdd(false)
    await loadWorkers()
  }

  function startEdit(w) {
    setEditingId(w.id)
    setEditDraft({ name: w.name, vest_id: w.vest_id, zone: w.zone || '' })
  }

  async function saveEdit(id) {
    await api.patch(`workers/${id}/`, { name: editDraft.name, vest_id: editDraft.vest_id, zone: editDraft.zone })
    setEditingId(null)
    await loadWorkers()
  }

  async function toggleActive(w) {
    await api.patch(`workers/${w.id}/`, { is_active: !w.is_active })
    await loadWorkers()
  }

  async function removeWorker(w) {
    const ok = window.confirm(`Delete worker ${w.name} (${w.vest_id})?`)
    if (!ok) return
    setDeletingId(w.id)
    try {
      await api.delete(`workers/${w.id}/`)
      if (editingId === w.id) setEditingId(null)
      await loadWorkers()
    } finally {
      setDeletingId(null)
    }
  }

  const activeCount = workers.filter((w) => w.is_active).length

  return (
    <div className="page workers-page">
      <div className="page__header-row">
        <div>
          <p className="page__eyebrow">Personnel</p>
          <h1 className="page__title">Workers</h1>
          <p className="page__lead">
            {workers.length} registered &middot; {activeCount} active on site
          </p>
        </div>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => setShowAdd((s) => !s)}
        >
          {showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Worker</>}
        </button>
      </div>

      {showAdd ? (
        <form className="inline-form" onSubmit={handleCreate}>
          <h2 className="inline-form__title">Register new worker</h2>
          <div className="inline-form__grid">
            <label className="field">
              <span className="field__label">Full Name</span>
              <input
                className="field__input"
                placeholder="e.g. Ahmed Hassan"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Vest ID</span>
              <input
                className="field__input"
                placeholder="e.g. VEST-042"
                value={form.vest_id}
                onChange={(e) => setForm((f) => ({ ...f, vest_id: e.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Zone (optional)</span>
              <input
                className="field__input"
                placeholder="e.g. Block A, Rooftop"
                value={form.zone}
                onChange={(e) => setForm((f) => ({ ...f, zone: e.target.value }))}
              />
            </label>
          </div>
          <div className="inline-form__actions">
            <button type="submit" className="btn btn--primary">
              Save Worker
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => setShowAdd(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {workers.length === 0 ? (
        <div className="panel" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.4 }}>👷</div>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>No workers yet. Add your first worker above.</p>
        </div>
      ) : (
        <div className="workers-grid">
          {workers.map((w) =>
            editingId === w.id ? (
              /* Edit card */
              <div key={w.id} className="worker-card">
                <h3 style={{ margin: '0 0 0.85rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Editing — {w.name}
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginBottom: '0.85rem' }}>
                  <label className="field">
                    <span className="field__label">Name</span>
                    <input
                      className="field__input field__input--table"
                      value={editDraft.name}
                      onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">Vest ID</span>
                    <input
                      className="field__input field__input--table"
                      value={editDraft.vest_id}
                      onChange={(e) => setEditDraft((d) => ({ ...d, vest_id: e.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">Zone</span>
                    <input
                      className="field__input field__input--table"
                      value={editDraft.zone}
                      onChange={(e) => setEditDraft((d) => ({ ...d, zone: e.target.value }))}
                    />
                  </label>
                </div>
                <div className="worker-card__actions">
                  <button type="button" className="btn btn--sm btn--primary" onClick={() => saveEdit(w.id)}>
                    Save
                  </button>
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => setEditingId(null)}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              /* Display card */
              <div key={w.id} className="worker-card">
                <div className="worker-card__header">
                  <div className="worker-card__avatar">{initials(w.name)}</div>
                  <div className="worker-card__info">
                    <p className="worker-card__name">{w.name}</p>
                    <p className="worker-card__vest">{w.vest_id}</p>
                  </div>
                  <span className={w.is_active ? 'badge badge--low' : 'badge badge--medium'}>
                    {w.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {w.zone ? (
                  <div className="worker-card__meta">
                    <span className="worker-card__zone-chip">
                      <IconMapPin />
                      {w.zone}
                    </span>
                  </div>
                ) : (
                  <div className="worker-card__meta">
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>No zone assigned</span>
                  </div>
                )}

                <div className="worker-card__actions">
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => startEdit(w)}>
                    Edit
                  </button>
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => toggleActive(w)}>
                    {w.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button
                    type="button"
                    className="btn btn--sm btn--danger"
                    disabled={deletingId === w.id}
                    onClick={() => removeWorker(w)}
                  >
                    {deletingId === w.id ? '…' : 'Delete'}
                  </button>
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  )
}
