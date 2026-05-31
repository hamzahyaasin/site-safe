function formatLastSeen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function batteryClass(level) {
  if (level == null) return 'vest-battery__fill--unknown'
  if (level < 20) return 'vest-battery__fill--low'
  if (level < 40) return 'vest-battery__fill--medium'
  return 'vest-battery__fill--high'
}

function formatGps(vest) {
  if (vest.latitude != null && vest.longitude != null) {
    return `${vest.latitude.toFixed(5)}, ${vest.longitude.toFixed(5)}`
  }
  return 'No fix'
}

function BatteryIndicator({ level }) {
  const pct = level == null ? 0 : Math.max(0, Math.min(100, level))
  return (
    <div className="vest-battery">
      <div className="vest-battery__track">
        <div className={`vest-battery__fill ${batteryClass(level)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="vest-battery__label">{level == null ? '—' : `${pct}%`}</span>
    </div>
  )
}

function OnlineDot({ isOnline }) {
  return (
    <span className="vest-online">
      <span className={`vest-online__dot ${isOnline ? 'vest-online__dot--on' : 'vest-online__dot--off'}`} />
      {isOnline ? 'Online' : 'Offline'}
    </span>
  )
}

export default function VestTable({ vests, loading, selectedId, onSelect }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Vest ID</th>
            <th>Assigned Worker</th>
            <th>Battery</th>
            <th>GPS</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={7} className="empty-cell">
                Loading vests…
              </td>
            </tr>
          ) : vests.length === 0 ? (
            <tr>
              <td colSpan={7} className="empty-cell">
                No smart vests registered yet.
              </td>
            </tr>
          ) : (
            vests.map((vest) => (
              <tr
                key={vest.id}
                className={selectedId === vest.id ? 'data-table__row data-table__row--selected' : 'data-table__row'}
              >
                <td>
                  <code>{vest.vest_id}</code>
                </td>
                <td>{vest.worker_name || <span className="muted">Unassigned</span>}</td>
                <td>
                  <BatteryIndicator level={vest.battery_level} />
                </td>
                <td>
                  <span className={vest.latitude != null ? 'vest-gps vest-gps--fix' : 'vest-gps vest-gps--none'}>
                    {formatGps(vest)}
                  </span>
                </td>
                <td>
                  <OnlineDot isOnline={vest.is_online} />
                  {vest.sos_active ? <span className="badge badge--critical vest-sos-badge">SOS</span> : null}
                </td>
                <td>{formatLastSeen(vest.last_seen)}</td>
                <td className="actions-cell">
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => onSelect(vest)}>
                    {selectedId === vest.id ? 'Selected' : 'View'}
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
