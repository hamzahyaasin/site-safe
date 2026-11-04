import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Drawer from '../ui/Drawer.jsx'
import Input, { Select } from '../ui/Input.jsx'
import { cn, formatTimestamp } from '../../lib/utils.js'

/** Slide-over for one vest's live telemetry and worker assignment, or for registering a new vest. */
export default function VestDrawer({
  open,
  vest,
  workers,
  workersLoading,
  onAssignWorker,
  assigning,
  canEdit = false,
  onClose,
  registerForm,
  onRegisterChange,
  onRegister,
  registerSaving,
  mode,
}) {
  if (mode === 'register') {
    return (
      <Drawer
        open={open}
        onClose={onClose}
        title="Register vest"
        description="Add a new smart vest to the fleet"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" form="register-vest-form" variant="primary" loading={registerSaving} disabled={!registerForm.vest_id.trim()}>
              Register vest
            </Button>
          </div>
        }
      >
        <form
          id="register-vest-form"
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            onRegister()
          }}
        >
          <Input
            label="Vest ID"
            value={registerForm.vest_id}
            onChange={(e) => onRegisterChange({ ...registerForm, vest_id: e.target.value })}
            placeholder="VEST-001"
            hint="The id flashed into the vest firmware (VEST_ID in config.h)."
            required
          />
          <Input
            label="Firmware version"
            value={registerForm.firmware_version}
            onChange={(e) => onRegisterChange({ ...registerForm, firmware_version: e.target.value })}
            placeholder="1.0.0"
          />
        </form>
      </Drawer>
    )
  }

  if (!vest) return null

  const pct = vest.battery_level == null ? 0 : Math.max(0, Math.min(100, vest.battery_level))
  const hasGps = vest.is_online && vest.latitude != null && vest.longitude != null

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={<span className="font-mono">{vest.vest_id}</span>}
      description={`Last seen ${formatTimestamp(vest.last_seen)}`}
      footer={
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Done
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="flex flex-wrap gap-2">
          <Badge variant={vest.is_online ? 'active' : 'offline'} dot>
            {vest.is_online ? 'Online' : 'Offline'}
          </Badge>
          {vest.sos_active ? <Badge variant="critical" dot>SOS active</Badge> : null}
        </div>

        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Telemetry</h3>
          <dl className="mt-2 divide-y divide-zinc-800 rounded-lg border border-zinc-800 bg-zinc-900/40">
            <Row label="GPS">
              {hasGps ? (
                <span className="font-mono text-zinc-200">
                  {vest.latitude.toFixed(5)}, {vest.longitude.toFixed(5)}
                </span>
              ) : (
                <span className="text-zinc-500">{vest.is_online ? 'Awaiting fix…' : 'No fix (offline)'}</span>
              )}
            </Row>
            <Row label="Battery">
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800">
                  <span
                    className={cn('block h-full rounded-full', pct < 20 ? 'bg-red-500' : pct < 40 ? 'bg-amber-500' : 'bg-emerald-500')}
                    style={{ width: `${pct}%` }}
                  />
                </span>
                <span className="tabular-nums text-zinc-300">{vest.battery_level == null ? 'not reported' : `${pct}%`}</span>
              </span>
            </Row>
            <Row label="SOS">
              {vest.sos_active ? (
                <span className="font-semibold text-red-400">Active — emergency signal</span>
              ) : (
                <span className="text-zinc-300">Normal</span>
              )}
            </Row>
            <Row label="Firmware">
              <span className="font-mono text-zinc-300">{vest.firmware_version || '—'}</span>
            </Row>
          </dl>
        </section>

        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Assignment</h3>
          <Select
            label="Assigned worker"
            className="mt-2"
            value={vest.worker ?? ''}
            disabled={!canEdit || assigning || workersLoading}
            onChange={(e) => {
              const val = e.target.value
              onAssignWorker(val ? Number(val) : null)
            }}
            hint={
              canEdit
                ? 'Only active workers without a vest are listed. The change saves immediately.'
                : 'Assigning vests needs the Safety Officer or Admin role.'
            }
          >
            <option value="">Unassigned</option>
            {workers
              .filter((w) => w.is_active && (!w.smart_vest || w.smart_vest.id === vest.id))
              .map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
          </Select>
        </section>
      </div>
    </Drawer>
  )
}

function Row({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-4 px-3.5 py-2.5 text-sm">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  )
}
