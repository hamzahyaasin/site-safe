import { useState } from 'react'
import VestDrawer from '../components/vests/VestDrawer.jsx'
import VestTable from '../components/vests/VestTable.jsx'
import { useVests } from '../hooks/useVests.js'
import { useWorkers } from '../hooks/useWorkers.js'

const emptyRegisterForm = { vest_id: '', firmware_version: '' }

export default function VestManagementPage() {
  const { vests, loading, error, createVest, updateVest, fetchVests } = useVests()
  const { workers, loading: workersLoading } = useWorkers()
  const [selected, setSelected] = useState(null)
  const [mode, setMode] = useState('view')
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm)
  const [assigning, setAssigning] = useState(false)
  const [registerSaving, setRegisterSaving] = useState(false)
  const [toast, setToast] = useState('')

  function showToast(msg) {
    setToast(msg)
    window.setTimeout(() => setToast(''), 3500)
  }

  function selectVest(vest) {
    setSelected(vest)
    setMode('view')
  }

  function startRegister() {
    setSelected(null)
    setMode('register')
    setRegisterForm(emptyRegisterForm)
  }

  async function handleAssignWorker(workerId) {
    if (!selected) return
    setAssigning(true)
    try {
      const updated = await updateVest(selected.id, { worker: workerId })
      setSelected(updated)
      showToast(workerId ? 'Worker assigned to vest' : 'Vest unassigned')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to update assignment')
    } finally {
      setAssigning(false)
    }
  }

  async function handleRegister() {
    setRegisterSaving(true)
    try {
      const created = await createVest({
        vest_id: registerForm.vest_id.trim(),
        firmware_version: registerForm.firmware_version.trim(),
      })
      setMode('view')
      setSelected(created)
      setRegisterForm(emptyRegisterForm)
      showToast('Vest registered')
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to register vest')
    } finally {
      setRegisterSaving(false)
    }
  }

  return (
    <div className="page vest-management-page">
      <header className="page-header page-header--split">
        <div>
          <h1 className="page__title">Vest Management</h1>
          <p className="page__lead">Monitor IoT smart vests, telemetry, and worker assignments</p>
        </div>
        <div className="page-header__actions">
          <button type="button" className="btn btn--ghost" onClick={() => fetchVests()}>
            Refresh
          </button>
          <button type="button" className="btn btn--primary" onClick={startRegister}>
            Register vest
          </button>
        </div>
      </header>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="vest-layout">
        <div className="vest-layout__table">
          <VestTable vests={vests} loading={loading} selectedId={selected?.id} onSelect={selectVest} />
        </div>
        <div className="vest-layout__drawer">
          <VestDrawer
            vest={selected}
            workers={workers}
            workersLoading={workersLoading}
            onAssignWorker={handleAssignWorker}
            assigning={assigning}
            mode={mode}
            registerForm={registerForm}
            onRegisterChange={setRegisterForm}
            onRegister={handleRegister}
            registerSaving={registerSaving}
            onClose={() => {
              setSelected(null)
              setMode('view')
              setRegisterForm(emptyRegisterForm)
            }}
          />
        </div>
      </div>

      {toast ? (
        <div className="toast toast--success" role="status">
          {toast}
        </div>
      ) : null}
    </div>
  )
}
