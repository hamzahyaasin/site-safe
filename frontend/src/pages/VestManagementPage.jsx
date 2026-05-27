import { useState } from 'react'
import { useWorkers } from '../hooks/useWorkers.js'
import VestDrawer from '../components/vests/VestDrawer.jsx'
import VestTable from '../components/vests/VestTable.jsx'
import Button from '../components/ui/Button.jsx'

const emptyForm = { name: '', vest_id: '', zone: '' }

export default function VestManagementPage() {
  const { workers, loading, createWorker, updateWorker } = useWorkers()
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [mode, setMode] = useState('edit')
  const [saving, setSaving] = useState(false)

  function selectWorker(worker) {
    setSelected(worker)
    setMode('edit')
    setForm({ name: worker.name, vest_id: worker.vest_id, zone: worker.zone || '' })
  }

  function startRegister() {
    setSelected(null)
    setMode('register')
    setForm(emptyForm)
  }

  async function handleSave() {
    setSaving(true)
    try {
      if (mode === 'register') {
        await createWorker(form)
        setMode('edit')
        setForm(emptyForm)
      } else if (selected) {
        await updateWorker(selected.id, form)
        setSelected((prev) => (prev ? { ...prev, ...form } : null))
      }
    } finally {
      setSaving(false)
    }
  }

  function handleAssign(worker) {
    selectWorker(worker)
  }

  function handleUnassign(worker) {
    updateWorker(worker.id, { zone: '' })
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Vest Management</h1>
          <p className="mt-1 text-sm text-zinc-500">Register, assign, and monitor IoT safety vests</p>
        </div>
        <Button variant="primary" size="sm" onClick={startRegister}>
          Register vest
        </Button>
      </header>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <VestTable
            workers={workers}
            loading={loading}
            selectedId={selected?.id}
            onSelect={selectWorker}
            onAssign={handleAssign}
            onUnassign={handleUnassign}
          />
        </div>
        <div className="xl:col-span-5">
          <VestDrawer
            worker={selected}
            form={form}
            onChange={setForm}
            onSave={handleSave}
            onClose={() => {
              setSelected(null)
              setMode('edit')
              setForm(emptyForm)
            }}
            saving={saving}
            mode={mode}
          />
        </div>
      </div>
    </div>
  )
}
