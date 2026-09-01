import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Input from '../components/ui/Input.jsx'
import { cn, formatAlertType } from '../lib/utils.js'
import { useSettings } from '../hooks/useSettings.js'

const TABS = [
  { id: 'alerts', label: 'Alert Configuration' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'profile', label: 'Profile' },
]

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50',
        checked ? 'bg-amber-500' : 'bg-zinc-700',
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform',
          checked ? 'translate-x-4' : 'translate-x-0.5',
        )}
      />
    </button>
  )
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

  const configColumns = [
    { key: 'zone', header: 'Zone', render: (row) => row.zone_name || 'Global' },
    { key: 'alert_type', header: 'Alert Type', render: (row) => formatAlertType(row.alert_type) },
    {
      key: 'enabled',
      header: 'Enabled',
      render: (row) => <Toggle checked={row.is_enabled} onChange={() => handleToggleEnabled(row)} />,
    },
    { key: 'threshold', header: 'Threshold (sec)', render: (row) => row.threshold_seconds },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <Button variant="ghost" size="sm" onClick={() => openEditModal(row)}>
          Edit
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-100">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">Configure alerts, notifications, and your account</p>
      </header>

      <div className="flex gap-1 border-b border-zinc-800" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={cn(
              'border-b-2 px-3 py-2 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'border-amber-500 text-amber-400'
                : 'border-transparent text-zinc-500 hover:text-zinc-300',
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {activeTab === 'alerts' ? (
        <Card>
          <CardHeader>
            <CardTitle>Alert Configuration</CardTitle>
            <CardDescription>Per-zone alert rules, thresholds, and enablement</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <DataTable
              columns={configColumns}
              data={alertConfigs}
              loading={loadingConfigs}
              emptyTitle="No alert configuration entries yet"
              rowKey={(row) => row.id}
            />
          </CardContent>
        </Card>
      ) : null}

      {activeTab === 'notifications' ? (
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>Control how you receive safety alerts</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingProfile ? (
              <p className="text-sm text-zinc-500">Loading preferences…</p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-200">Push notifications (FCM)</p>
                    <p className="text-xs text-zinc-500">Receive mobile push alerts for critical incidents</p>
                  </div>
                  <Toggle
                    checked={!!profile?.notify_push}
                    disabled={notifSaving}
                    onChange={() => handleNotificationToggle('notify_push')}
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-200">Email notifications</p>
                    <p className="text-xs text-zinc-500">Receive alert summaries and escalations by email</p>
                  </div>
                  <Toggle
                    checked={!!profile?.notify_email}
                    disabled={notifSaving}
                    onChange={() => handleNotificationToggle('notify_email')}
                  />
                </div>
                {notifMsg ? <p className="text-xs text-emerald-400">{notifMsg}</p> : null}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {activeTab === 'profile' ? (
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingProfile ? (
              <p className="text-sm text-zinc-500">Loading profile…</p>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 max-w-md">
                  <Input label="Name" value={profile?.full_name || '—'} readOnly />
                  <Input label="Email" value={profile?.email || '—'} readOnly />
                </div>

                <h3 className="mb-3 mt-6 text-sm font-semibold text-zinc-100">Change password</h3>
                <form className="max-w-sm space-y-3" onSubmit={handlePasswordSubmit}>
                  <Input
                    label="Current password"
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, current_password: e.target.value }))}
                    required
                  />
                  <Input
                    label="New password"
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                    minLength={8}
                    required
                  />
                  <Input
                    label="Confirm new password"
                    type="password"
                    value={passwordForm.confirm_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, confirm_password: e.target.value }))}
                    minLength={8}
                    required
                  />
                  {passwordError ? (
                    <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
                      {passwordError}
                    </p>
                  ) : null}
                  {passwordSuccess ? (
                    <p className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300" role="status">
                      {passwordSuccess}
                    </p>
                  ) : null}
                  <Button type="submit" variant="primary" disabled={passwordSaving}>
                    {passwordSaving ? 'Updating…' : 'Update password'}
                  </Button>
                </form>
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Drawer
        open={!!editingConfig}
        onClose={closeEditModal}
        title="Edit Alert Rule"
        description={editingConfig ? `${editingConfig.zone_name || 'Global'} · ${formatAlertType(editingConfig.alert_type)}` : ''}
        footer={
          <div className="flex gap-2">
            <Button type="submit" form="alert-config-form" variant="primary" disabled={savingConfig}>
              {savingConfig ? 'Saving…' : 'Save'}
            </Button>
            <Button type="button" variant="ghost" onClick={closeEditModal}>
              Cancel
            </Button>
          </div>
        }
      >
        <form id="alert-config-form" className="space-y-4" onSubmit={saveConfigEdit}>
          <div className="flex items-center gap-2">
            <Toggle
              checked={editDraft.is_enabled}
              onChange={(val) => setEditDraft((d) => ({ ...d, is_enabled: val }))}
            />
            <span className="text-sm text-zinc-300">Enabled</span>
          </div>
          <Input
            label="Threshold (seconds)"
            type="number"
            min={0}
            value={editDraft.threshold_seconds}
            onChange={(e) => setEditDraft((d) => ({ ...d, threshold_seconds: e.target.value }))}
          />
          <p className="-mt-2 text-xs text-zinc-600">Used for inactivity alerts before triggering</p>
          {configError ? (
            <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400" role="alert">
              {configError}
            </p>
          ) : null}
        </form>
      </Drawer>
    </div>
  )
}
