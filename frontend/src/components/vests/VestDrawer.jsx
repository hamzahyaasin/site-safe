import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Input, { Select } from '../ui/Input.jsx'
import { formatTimestamp } from '../../lib/utils.js'

export default function VestDrawer({
  vest,
  workers,
  workersLoading,
  onAssignWorker,
  assigning,
  onClose,
  registerForm,
  onRegisterChange,
  onRegister,
  registerSaving,
  mode,
}) {
  if (mode === 'register') {
    return (
      <div className="flex h-full flex-col rounded-lg border border-zinc-800 bg-[#151821]">
        <div className="border-b border-zinc-800 px-5 py-4">
          <h2 className="text-base font-semibold text-zinc-100">Register Vest</h2>
          <p className="mt-0.5 text-xs text-zinc-500">Add a new smart vest to the fleet</p>
        </div>
        <form
          className="flex flex-1 flex-col overflow-y-auto px-5 py-4 scrollbar-thin"
          onSubmit={(e) => {
            e.preventDefault()
            onRegister()
          }}
        >
          <div className="space-y-4">
            <Input
              label="Vest ID"
              value={registerForm.vest_id}
              onChange={(e) => onRegisterChange({ ...registerForm, vest_id: e.target.value })}
              placeholder="VEST-001"
              required
            />
            <Input
              label="Firmware version"
              value={registerForm.firmware_version}
              onChange={(e) => onRegisterChange({ ...registerForm, firmware_version: e.target.value })}
              placeholder="1.0.0"
            />
          </div>
          <div className="mt-auto flex gap-2 border-t border-zinc-800 pt-4">
            <Button type="submit" variant="primary" disabled={registerSaving}>
              {registerSaving ? 'Registering…' : 'Register vest'}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    )
  }

  if (!vest) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-zinc-900/20 p-8 text-center">
        <p className="text-sm font-medium text-zinc-400">Select a vest</p>
        <p className="mt-1 text-xs text-zinc-600">Choose a row from the table to view telemetry and assign a worker.</p>
      </div>
    )
  }

  const pct = vest.battery_level == null ? 0 : Math.max(0, Math.min(100, vest.battery_level))
  const hasGps = vest.is_online && vest.latitude != null && vest.longitude != null

  return (
    <div className="flex h-full flex-col rounded-lg border border-zinc-800 bg-[#151821]">
      <div className="border-b border-zinc-800 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">{vest.vest_id}</h2>
            <p className="mt-0.5 text-xs text-zinc-500">Last seen {formatTimestamp(vest.last_seen)}</p>
          </div>
          <Badge variant={vest.is_online ? 'active' : 'offline'}>{vest.is_online ? 'Online' : 'Offline'}</Badge>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin">
        <div className="space-y-4">
          <section>
            <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-600">Telemetry</p>
            <dl className="mt-2 space-y-3">
              <div className="flex items-center justify-between">
                <dt className="text-xs text-zinc-500">GPS</dt>
                <dd className="text-right text-xs">
                  {hasGps ? (
                    <span className="font-mono text-zinc-300">
                      {vest.latitude.toFixed(5)}, {vest.longitude.toFixed(5)}
                    </span>
                  ) : (
                    <span className="text-zinc-600">{vest.is_online ? 'Awaiting fix…' : 'No fix (offline)'}</span>
                  )}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-xs text-zinc-500">Battery</dt>
                <dd className="flex items-center gap-2">
                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className={`h-full rounded-full ${pct < 20 ? 'bg-red-500' : pct < 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums text-zinc-400">{pct}%</span>
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-xs text-zinc-500">SOS</dt>
                <dd>
                  {vest.sos_active ? (
                    <Badge variant="critical">Active — emergency signal</Badge>
                  ) : (
                    <span className="text-xs text-zinc-400">Normal</span>
                  )}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-xs text-zinc-500">Firmware</dt>
                <dd className="text-xs text-zinc-400">{vest.firmware_version || '—'}</dd>
              </div>
            </dl>
          </section>

          <section className="border-t border-zinc-800 pt-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-600">Assignment</p>
            <Select
              label="Assign worker"
              className="mt-2"
              value={vest.worker ?? ''}
              disabled={assigning || workersLoading}
              onChange={(e) => {
                const val = e.target.value
                onAssignWorker(val ? Number(val) : null)
              }}
            >
              <option value="">Unassigned</option>
              {workers.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </Select>
            {vest.worker_name ? (
              <p className="mt-1.5 text-xs text-zinc-500">Currently assigned to {vest.worker_name}</p>
            ) : null}
          </section>
        </div>
      </div>

      <div className="border-t border-zinc-800 px-5 py-4">
        <Button type="button" variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
    </div>
  )
}
