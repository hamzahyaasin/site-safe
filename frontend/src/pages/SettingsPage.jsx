import { useState } from 'react'
import { useSettings } from '../hooks/useSettings.js'

const TABS = [
  { id: 'alerts', label: 'Alert Configuration' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'profile', label: 'Profile' },
]

function formatAlertType(type) {
  return type ? String(type).replace(/_/g, ' ') : '—'
}

export default function SettingsPage() {
  const {
    alertConfigs,
    profile,
    loadingConfigs,
    loadingProfile,
    error,
    updateAlertConfig,
    updateNotifications,
    changePassword,
  } = useSettings()

  const [activeTab, setActiveTab] = useState('alerts')
  const [editingConfig, setEditingConfig] = useState(null)
  const [editDraft, setEditDraft] = useState({ threshold_seconds: 300, is_enabled: true })
  const [configError, setConfigError] = useState('')
  const [savingConfig, setSavingConfig] = useState(false)
  const [notifSaving, setNotifSaving] = useState(false)
  const [notifMsg, setNotifMsg] = useState('')
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)

  async function handleToggleEnabled(config) {
    try {
      await updateAlertConfig(config.id, { is_enabled: !config.is_enabled })
    } catch (e) {
      window.alert(e.response?.data?.detail || 'Failed to update configuration')
    }
  }

  function openEditModal(config) {
    setEditingConfig(config)
    setEditDraft({
      threshold_seconds: config.threshold_seconds,
      is_enabled: config.is_enabled,
    })
    setConfigError('')
  }

  function closeEditModal() {
    setEditingConfig(null)
    setConfigError('')
  }

  async function saveConfigEdit(e) {
    e.preventDefault()
    if (!editingConfig) return
    setSavingConfig(true)
    setConfigError('')
    try {
      await updateAlertConfig(editingConfig.id, {
        threshold_seconds: Number(editDraft.threshold_seconds) || 0,
        is_enabled: editDraft.is_enabled,
      })
      closeEditModal()
    } catch (e) {
      setConfigError(e.response?.data?.detail || 'Failed to save configuration')
    } finally {
      setSavingConfig(false)
    }
  }

  async function handleNotificationToggle(field) {
    if (!profile) return
    setNotifSaving(true)
    setNotifMsg('')
    try {
      await updateNotifications({ [field]: !profile[field] })
      setNotifMsg('Notification preferences saved.')
    } catch (e) {
      setNotifMsg(e.response?.data?.detail || 'Failed to save preferences')
    } finally {
      setNotifSaving(false)
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('New passwords do not match.')
      return
    }
    setPasswordSaving(true)
    try {
      await changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })
      setPasswordSuccess('Password updated successfully.')
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (e) {
      const detail = e.response?.data
      if (typeof detail === 'object' && detail?.current_password) {
        setPasswordError(Array.isArray(detail.current_password) ? detail.current_password[0] : detail.current_password)
      } else {
        setPasswordError(detail?.detail || e.message || 'Failed to change password')
      }
    } finally {
      setPasswordSaving(false)
    }
  }

  return (
    <div className="page settings-page">
      <header className="page-header">
        <div>
          <h1 className="page__title">Settings</h1>
          <p className="page__lead">Configure alerts, notifications, and your account</p>
        </div>
      </header>

      <div className="settings-tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? 'settings-tab settings-tab--active' : 'settings-tab'}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {activeTab === 'alerts' ? (
        <section className="settings-panel">
          <h2 className="inline-form__title">Alert Configuration</h2>
          <p className="panel__muted">Per-zone alert rules, thresholds, and enablement</p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Zone</th>
                  <th>Alert Type</th>
                  <th>Enabled</th>
                  <th>Threshold (sec)</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loadingConfigs ? (
                  <tr>
                    <td colSpan={5} className="empty-cell">
                      Loading configuration…
                    </td>
                  </tr>
                ) : alertConfigs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty-cell">
                      No alert configuration entries yet.
                    </td>
                  </tr>
                ) : (
                  alertConfigs.map((config) => (
                    <tr key={config.id}>
                      <td>{config.zone_name || 'Global'}</td>
                      <td>{formatAlertType(config.alert_type)}</td>
                      <td>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={config.is_enabled}
                            onChange={() => handleToggleEnabled(config)}
                          />
                          <span className="toggle-switch__slider" />
                        </label>
                      </td>
                      <td>{config.threshold_seconds}</td>
                      <td className="actions-cell">
                        <button
                          type="button"
                          className="btn btn--sm btn--ghost"
                          onClick={() => openEditModal(config)}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activeTab === 'notifications' ? (
        <section className="settings-panel">
          <h2 className="inline-form__title">Notifications</h2>
          <p className="panel__muted">Control how you receive safety alerts</p>
          {loadingProfile ? (
            <p className="muted">Loading preferences…</p>
          ) : (
            <div className="notification-toggles">
              <label className="notification-toggle-row">
                <div>
                  <strong>Push notifications (FCM)</strong>
                  <p className="field__hint">Receive mobile push alerts for critical incidents</p>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={!!profile?.notify_push}
                    disabled={notifSaving}
                    onChange={() => handleNotificationToggle('notify_push')}
                  />
                  <span className="toggle-switch__slider" />
                </label>
              </label>
              <label className="notification-toggle-row">
                <div>
                  <strong>Email notifications</strong>
                  <p className="field__hint">Receive alert summaries and escalations by email</p>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={!!profile?.notify_email}
                    disabled={notifSaving}
                    onChange={() => handleNotificationToggle('notify_email')}
                  />
                  <span className="toggle-switch__slider" />
                </label>
              </label>
              {notifMsg ? <p className="form-success">{notifMsg}</p> : null}
            </div>
          )}
        </section>
      ) : null}

      {activeTab === 'profile' ? (
        <section className="settings-panel">
          <h2 className="inline-form__title">Profile</h2>
          {loadingProfile ? (
            <p className="muted">Loading profile…</p>
          ) : (
            <>
              <div className="profile-readonly inline-form__grid">
                <label className="field">
                  <span className="field__label">Name</span>
                  <input className="field__input" value={profile?.full_name || '—'} readOnly />
                </label>
                <label className="field">
                  <span className="field__label">Email</span>
                  <input className="field__input" value={profile?.email || '—'} readOnly />
                </label>
              </div>

              <h3 className="settings-subtitle">Change password</h3>
              <form className="password-form" onSubmit={handlePasswordSubmit}>
                <label className="field">
                  <span className="field__label">Current password</span>
                  <input
                    className="field__input"
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(e) =>
                      setPasswordForm((f) => ({ ...f, current_password: e.target.value }))
                    }
                    required
                  />
                </label>
                <label className="field">
                  <span className="field__label">New password</span>
                  <input
                    className="field__input"
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                    minLength={8}
                    required
                  />
                </label>
                <label className="field">
                  <span className="field__label">Confirm new password</span>
                  <input
                    className="field__input"
                    type="password"
                    value={passwordForm.confirm_password}
                    onChange={(e) =>
                      setPasswordForm((f) => ({ ...f, confirm_password: e.target.value }))
                    }
                    minLength={8}
                    required
                  />
                </label>
                {passwordError ? (
                  <p className="form-error" role="alert">
                    {passwordError}
                  </p>
                ) : null}
                {passwordSuccess ? (
                  <p className="form-success" role="status">
                    {passwordSuccess}
                  </p>
                ) : null}
                <div className="inline-form__actions">
                  <button type="submit" className="btn btn--primary" disabled={passwordSaving}>
                    {passwordSaving ? 'Updating…' : 'Update password'}
                  </button>
                </div>
              </form>
            </>
          )}
        </section>
      ) : null}

      {editingConfig ? (
        <div className="modal-backdrop" role="presentation" onClick={closeEditModal}>
          <div
            className="modal-panel"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="modal-panel__header">
              <h2 className="modal-panel__title">Edit Alert Rule</h2>
              <button type="button" className="btn btn--ghost btn--sm" onClick={closeEditModal}>
                ✕
              </button>
            </header>
            <form className="modal-panel__form" onSubmit={saveConfigEdit}>
              <p className="muted">
                {editingConfig.zone_name || 'Global'} · {formatAlertType(editingConfig.alert_type)}
              </p>
              <label className="field field--checkbox">
                <input
                  type="checkbox"
                  checked={editDraft.is_enabled}
                  onChange={(e) => setEditDraft((d) => ({ ...d, is_enabled: e.target.checked }))}
                />
                <span>Enabled</span>
              </label>
              <label className="field">
                <span className="field__label">Threshold (seconds)</span>
                <input
                  className="field__input"
                  type="number"
                  min={0}
                  value={editDraft.threshold_seconds}
                  onChange={(e) =>
                    setEditDraft((d) => ({ ...d, threshold_seconds: e.target.value }))
                  }
                />
                <span className="field__hint">Used for inactivity alerts before triggering</span>
              </label>
              {configError ? (
                <p className="form-error" role="alert">
                  {configError}
                </p>
              ) : null}
              <div className="modal-panel__actions">
                <button type="submit" className="btn btn--primary" disabled={savingConfig}>
                  {savingConfig ? 'Saving…' : 'Save'}
                </button>
                <button type="button" className="btn btn--ghost" onClick={closeEditModal}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
