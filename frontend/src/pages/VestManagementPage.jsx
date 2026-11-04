import { useState } from 'react'
import VestDrawer from '../components/vests/VestDrawer.jsx'
import VestTable from '../components/vests/VestTable.jsx'
import Alert from '../components/ui/Alert.jsx'
import Button from '../components/ui/Button.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { IconPlus, IconRefresh } from '../components/ui/icons.jsx'
import { useVests } from '../hooks/useVests.js'
import { useWorkers } from '../hooks/useWorkers.js'
import { useAuth } from '../context/AuthContext.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'

const emptyRegisterForm = { vest_id: '', firmware_version: '' }

export default function VestManagementPage() {
  const { canOperate } = useAuth()
  const { toast } = useFeedback()
  const { vests, loading, error, createVest, updateVest, fetchVests } = useVests()
  const { workers, loading: workersLoading } = useWorkers()
  // The open vest is looked up by id, so its telemetry keeps updating while the panel is open.
  const [selectedId, setSelectedId] = useState(null)
  const [mode, setMode] = useState(null) // null | 'view' | 'register'
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm)
  const [assigning, setAssigning] = useState(false)
  const [registerSaving, setRegisterSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const selected = vests.find((v) => v.id === selectedId) ?? null

  const online = vests.filter((v) => v.is_online).length
  const assigned = vests.filter((v) => v.worker).length

  function selectVest(vest) {
    setSelectedId(vest.id)
    setMode('view')
  }

  function startRegister() {
    setSelectedId(null)
    setRegisterForm(emptyRegisterForm)
    setMode('register')
  }

  function close() {
    setMode(null)
    setSelectedId(null)
    setRegisterForm(emptyRegisterForm)
  }

  async function refresh() {
    setRefreshing(true)
    try {
      await fetchVests()
    } finally {
      setRefreshing(false)
    }
  }

  async function handleAssignWorker(workerId) {
    if (!selected) return
    setAssigning(true)
    try {
      await updateVest(selected.id, { worker: workerId })
      toast(workerId ? 'Worker assigned to vest' : 'Vest unassigned')
    } catch (e) {
      toast(e.response?.data?.worker?.[0] || apiErrorText(e, 'Failed to update assignment'), 'error')
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
      setRegisterForm(emptyRegisterForm)
      setSelectedId(created.id)
      setMode('view')
      toast(`Vest ${created.vest_id} registered`)
    } catch (e) {
      toast(apiErrorText(e, 'Failed to register vest'), 'error')
    } finally {
      setRegisterSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vest Management"
        description={
          loading
            ? 'Monitor IoT smart vests, telemetry, and worker assignments'
            : `${vests.length} vest${vests.length === 1 ? '' : 's'} · ${online} online · ${assigned} assigned to a worker`
        }
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={refresh} loading={refreshing}>
              {refreshing ? null : <IconRefresh className="h-3.5 w-3.5" />}
              Refresh
            </Button>
            {canOperate ? (
              <Button variant="primary" size="sm" onClick={startRegister}>
                <IconPlus className="h-3.5 w-3.5" />
                Register vest
              </Button>
            ) : null}
          </>
        }
      />

      {error ? <Alert>{typeof error === 'string' ? error : 'Could not load vests.'}</Alert> : null}

      <VestTable vests={vests} loading={loading} selectedId={selected?.id} onSelect={selectVest} />

      <VestDrawer
        open={mode !== null}
        vest={selected}
        workers={workers}
        workersLoading={workersLoading}
        onAssignWorker={handleAssignWorker}
        assigning={assigning}
        canEdit={canOperate}
        mode={mode}
        registerForm={registerForm}
        onRegisterChange={setRegisterForm}
        onRegister={handleRegister}
        registerSaving={registerSaving}
        onClose={close}
      />
    </div>
  )
}
