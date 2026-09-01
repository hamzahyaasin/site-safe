import { useState } from 'react'
import VestDrawer from '../components/vests/VestDrawer.jsx'
import VestTable from '../components/vests/VestTable.jsx'
import Button from '../components/ui/Button.jsx'
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
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Vest Management</h1>
          <p className="mt-1 text-sm text-zinc-500">Monitor IoT smart vests, telemetry, and worker assignments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => fetchVests()}>
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={startRegister}>
            Register vest
          </Button>
        </div>
      </header>

      {error ? (
        <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <VestTable vests={vests} loading={loading} selectedId={selected?.id} onSelect={selectVest} />
        </div>
        <div className="xl:col-span-5">
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
        <div
          className="fixed bottom-6 right-6 z-50 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300 shadow-lg"
          role="status"
        >
          {toast}
        </div>
      ) : null}
    </div>
  )
}
