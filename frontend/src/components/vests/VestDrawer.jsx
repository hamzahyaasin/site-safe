function formatLastSeen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function batteryBarClass(level) {
  if (level == null) return 'vest-drawer__battery-fill--unknown'
  if (level < 20) return 'vest-drawer__battery-fill--low'
  if (level < 40) return 'vest-drawer__battery-fill--medium'
  return 'vest-drawer__battery-fill--high'
}

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
      <aside className="vest-drawer">
        <header className="vest-drawer__header">
          <h2 className="vest-drawer__title">Register Vest</h2>
          <p className="vest-drawer__subtitle">Add a new smart vest to the fleet</p>
        </header>
        <form
          className="vest-drawer__body"
          onSubmit={(e) => {
            e.preventDefault()
            onRegister()
          }}
        >
          <label className="field">
            <span className="field__label">Vest ID</span>
            <input
              className="field__input"
              value={registerForm.vest_id}
              onChange={(e) => onRegisterChange({ ...registerForm, vest_id: e.target.value })}
              placeholder="VEST-001"
              required
            />
          </label>
          <label className="field">
            <span className="field__label">Firmware version</span>
            <input
              className="field__input"
              value={registerForm.firmware_version}
              onChange={(e) => onRegisterChange({ ...registerForm, firmware_version: e.target.value })}
              placeholder="1.0.0"
            />
          </label>
          <div className="vest-drawer__actions">
            <button type="submit" className="btn btn--primary" disabled={registerSaving}>
              {registerSaving ? 'Registering…' : 'Register vest'}
            </button>
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </aside>
    )
  }

  if (!vest) {
    return (
      <aside className="vest-drawer vest-drawer--empty">
        <p className="vest-drawer__empty-title">Select a vest</p>
        <p className="muted">Choose a row from the table to view telemetry and assign a worker.</p>
      </aside>
    )
  }

  const pct = vest.battery_level == null ? 0 : Math.max(0, Math.min(100, vest.battery_level))
  const hasGps = vest.is_online && vest.latitude != null && vest.longitude != null

  return (
    <aside className="vest-drawer">
      <header className="vest-drawer__header">
        <div className="vest-drawer__header-row">
          <div>
            <h2 className="vest-drawer__title">{vest.vest_id}</h2>
            <p className="vest-drawer__subtitle">Last seen {formatLastSeen(vest.last_seen)}</p>
          </div>
          <span className={`badge ${vest.is_online ? 'badge--low' : 'badge--medium'}`}>
            {vest.is_online ? 'Online' : 'Offline'}
          </span>
        </div>
      </header>

      <div className="vest-drawer__body">
        <section className="vest-drawer__section">
          <h3 className="vest-drawer__section-title">Telemetry</h3>
          <dl className="vest-drawer__stats">
            <div>
              <dt>GPS</dt>
              <dd>
                {hasGps ? (
                  <>
                    <span className="vest-gps vest-gps--fix">
                      {vest.latitude.toFixed(5)}, {vest.longitude.toFixed(5)}
                    </span>
                    <span className="field__hint">Live coordinates</span>
                  </>
                ) : (
                  <span className="muted">{vest.is_online ? 'Awaiting fix…' : 'No fix (offline)'}</span>
                )}
              </dd>
            </div>
            <div>
              <dt>Battery</dt>
              <dd>
                <div className="vest-drawer__battery-track">
                  <div
                    className={`vest-drawer__battery-fill ${batteryBarClass(vest.battery_level)}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="vest-drawer__battery-label">{pct}%</span>
              </dd>
            </div>
            <div>
              <dt>SOS</dt>
              <dd>
                <span className={`vest-sos ${vest.sos_active ? 'vest-sos--active' : 'vest-sos--idle'}`}>
                  {vest.sos_active ? 'ACTIVE — emergency signal' : 'Normal'}
                </span>
              </dd>
            </div>
            <div>
              <dt>Firmware</dt>
              <dd>{vest.firmware_version || '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="vest-drawer__section">
          <h3 className="vest-drawer__section-title">Assignment</h3>
          <label className="field">
            <span className="field__label">Assign worker</span>
            <select
              className="field__select"
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
                  {w.name} ({w.vest_id})
                </option>
              ))}
            </select>
          </label>
          {vest.worker_name ? (
            <p className="field__hint">Currently assigned to {vest.worker_name}</p>
          ) : null}
        </section>

        <div className="vest-drawer__actions">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </aside>
  )
}
