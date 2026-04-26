import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

const emptyForm = { name: '', vest_id: '', zone: '' }

export default function WorkersPage() {
  const { api } = useAuth()
  const [workers, setWorkers] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState(emptyForm)

  const loadWorkers = useCallback(async () => {
    const { data } = await api.get('workers/')
    setWorkers(Array.isArray(data) ? data : data.results || [])
  }, [api])

  useEffect(() => {
    loadWorkers()
  }, [loadWorkers])

  async function handleCreate(e) {
    e.preventDefault()
    await api.post('workers/', {
      name: form.name,
      vest_id: form.vest_id,
      zone: form.zone,
      is_active: true,
    })
    setForm(emptyForm)
    setShowAdd(false)
    await loadWorkers()
  }

  function startEdit(w) {
    setEditingId(w.id)
    setEditDraft({
      name: w.name,
      vest_id: w.vest_id,
      zone: w.zone || '',
    })
  }

  async function saveEdit(id) {
    await api.patch(`workers/${id}/`, {
      name: editDraft.name,
      vest_id: editDraft.vest_id,
      zone: editDraft.zone,
    })
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
    await api.delete(`workers/${w.id}/`)
    if (editingId === w.id) setEditingId(null)
    await loadWorkers()
  }

  return (
    <div className="page workers-page">
      <header className="page-header page-header--split">
        <div>
          <h1 className="page__title">Workers</h1>
          <p className="page__lead">Manage vests and site zones</p>
        </div>
        <button type="button" className="btn btn--primary" onClick={() => setShowAdd((s) => !s)}>
          {showAdd ? 'Close form' : 'Add Worker'}
        </button>
      </header>

      {showAdd ? (
        <form className="inline-form" onSubmit={handleCreate}>
          <h2 className="inline-form__title">New worker</h2>
          <div className="inline-form__grid">
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
              <span className="field__label">Vest ID</span>
              <input
                className="field__input"
                value={form.vest_id}
                onChange={(e) => setForm((f) => ({ ...f, vest_id: e.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span className="field__label">Zone</span>
              <input
                className="field__input"
                value={form.zone}
                onChange={(e) => setForm((f) => ({ ...f, zone: e.target.value }))}
              />
            </label>
          </div>
          <div className="inline-form__actions">
            <button type="submit" className="btn btn--primary">
              Save worker
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => setShowAdd(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Vest ID</th>
              <th>Zone</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {workers.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-cell">
                  No workers yet. Add one with the button above.
                </td>
              </tr>
            ) : (
              workers.map((w) =>
                editingId === w.id ? (
                  <tr key={w.id}>
                    <td>
                      <input
                        className="field__input field__input--table"
                        value={editDraft.name}
                        onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))}
                      />
                    </td>
                    <td>
                      <input
                        className="field__input field__input--table"
                        value={editDraft.vest_id}
                        onChange={(e) => setEditDraft((d) => ({ ...d, vest_id: e.target.value }))}
                      />
                    </td>
                    <td>
                      <input
                        className="field__input field__input--table"
                        value={editDraft.zone}
                        onChange={(e) => setEditDraft((d) => ({ ...d, zone: e.target.value }))}
                      />
                    </td>
                    <td>
                      <span className={w.is_active ? 'badge badge--low' : 'badge badge--medium'}>
                        {w.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="actions-cell">
                      <button type="button" className="btn btn--sm btn--primary" onClick={() => saveEdit(w.id)}>
                        Save
                      </button>
                      <button type="button" className="btn btn--sm btn--ghost" onClick={() => setEditingId(null)}>
                        Cancel
                      </button>
                    </td>
                  </tr>
                ) : (
                  <tr key={w.id}>
                    <td>{w.name}</td>
                    <td>
                      <code>{w.vest_id}</code>
                    </td>
                    <td>{w.zone || '—'}</td>
                    <td>
                      <span className={w.is_active ? 'badge badge--low' : 'badge badge--medium'}>
                        {w.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="actions-cell">
                      <button type="button" className="btn btn--sm btn--ghost" onClick={() => startEdit(w)}>
                        Edit
                      </button>
                      <button type="button" className="btn btn--sm btn--ghost" onClick={() => toggleActive(w)}>
                        {w.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button type="button" className="btn btn--sm btn--danger" onClick={() => removeWorker(w)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ),
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
