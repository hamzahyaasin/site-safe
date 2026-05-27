import Button from '../ui/Button.jsx'
import Input from '../ui/Input.jsx'
import Badge from '../ui/Badge.jsx'
import { formatTimestamp } from '../../lib/utils.js'

export default function VestDrawer({
  worker,
  form,
  onChange,
  onSave,
  onClose,
  saving,
  mode = 'edit',
}) {
  if (!worker && mode === 'edit') {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-zinc-900/20 p-8 text-center">
        <p className="text-sm font-medium text-zinc-400">Select a vest</p>
        <p className="mt-1 text-xs text-zinc-600">Choose a row from the table to view or edit details.</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-zinc-800 bg-[#151821]">
      <div className="border-b border-zinc-800 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              {mode === 'register' ? 'Register Vest' : worker.vest_id}
            </h2>
            <p className="mt-0.5 text-xs text-zinc-500">
              {mode === 'register'
                ? 'Assign a new smart vest to a worker'
                : `Last ping ${formatTimestamp(worker.created_at)}`}
            </p>
          </div>
          {worker ? (
            <Badge variant={worker.is_active ? 'active' : 'offline'}>
              {worker.is_active ? 'Online' : 'Offline'}
            </Badge>
          ) : null}
        </div>
      </div>

      <form
        className="flex flex-1 flex-col overflow-y-auto px-5 py-4 scrollbar-thin"
        onSubmit={(e) => {
          e.preventDefault()
          onSave()
        }}
      >
        <div className="space-y-4">
          <Input
            label="Worker name"
            value={form.name}
            onChange={(e) => onChange({ ...form, name: e.target.value })}
            placeholder="Full name"
            required
          />
          <Input
            label="Vest ID"
            value={form.vest_id}
            onChange={(e) => onChange({ ...form, vest_id: e.target.value })}
            placeholder="VEST-001"
            required
          />
          <Input
            label="Zone"
            value={form.zone}
            onChange={(e) => onChange({ ...form, zone: e.target.value })}
            placeholder="Block A, Level 2"
          />
        </div>

        {mode === 'edit' && worker ? (
          <div className="mt-6 rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-600">History</p>
            <ul className="mt-2 space-y-2 text-xs text-zinc-500">
              <li>Registered {formatTimestamp(worker.created_at)}</li>
              <li>Zone: {worker.zone || 'Not assigned'}</li>
              <li>Status: {worker.is_active ? 'Active on site' : 'Inactive'}</li>
            </ul>
          </div>
        ) : null}

        <div className="mt-auto flex gap-2 border-t border-zinc-800 pt-4">
          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? 'Saving…' : mode === 'register' ? 'Register' : 'Save changes'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}
