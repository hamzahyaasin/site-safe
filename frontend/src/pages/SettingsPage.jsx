import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Alert from '../components/ui/Alert.jsx'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.jsx'
import DataTable from '../components/ui/DataTable.jsx'
import Drawer from '../components/ui/Drawer.jsx'
import Input from '../components/ui/Input.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Switch from '../components/ui/Switch.jsx'
import { IconPencil } from '../components/ui/icons.jsx'
import { alertTypeTitle, cn } from '../lib/utils.js'
import { useSettings } from '../hooks/useSettings.js'
import { useAuth } from '../context/AuthContext.jsx'
import { apiErrorText, useFeedback } from '../context/FeedbackContext.jsx'

// Fire is never suppressed and SOS is the last resort: the API keeps both enabled.
const ALWAYS_ENABLED = new Set(['SOS', 'FIRE', 'GAS'])

const TABS = [
  { id: 'alerts', label: 'Alert Configuration' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'profile', label: 'Profile' },
]

const ROLE_LABEL = { ADMIN: 'Admin', SAFETY_OFFICER: 'Safety Officer', VIEWER: 'Viewer' }

export default function SettingsPage() {
  // Alert rules are site configuration: Admin-only on the server.
  const { isAdmin, role } = useAuth()
  const { toast } = useFeedback()
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

  // The tab is in the address (?tab=profile) so the user menu can link straight to it.
  const [params, setParams] = useSearchParams()
  const activeTab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab') : 'alerts'
  const setActiveTab = (id) => setParams(id === 'alerts' ? {} : { tab: id }, { replace: true })

  const [editingConfig, setEditingConfig] = useState(null)
  const [editDraft, setEditDraft] = useState({ threshold_seconds: 300, is_enabled: true })
  const [configError, setConfigError] = useState('')
  const [savingConfig, setSavingConfig] = useState(false)
  const [togglingId, setTogglingId] = useState(null)
  const [notifSaving, setNotifSaving] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordError, setPasswordError] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)

  async function handleToggleEnabled(config) {
    setTogglingId(config.id)
    try {
      await updateAlertConfig(config.id, { is_enabled: !config.is_enabled })
      toast(`${alertTypeTitle(config.alert_type)} alerts ${config.is_enabled ? 'turned off' : 'turned on'}`)
    } catch (e) {
      toast(apiErrorText(e, 'Failed to update configuration'), 'error')
    } finally {
      setTogglingId(null)
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
      toast(`${alertTypeTitle(editingConfig.alert_type)} rule saved`)
      closeEditModal()
    } catch (e) {
      setConfigError(apiErrorText(e, 'Failed to save configuration'))
    } finally {
      setSavingConfig(false)
    }
  }

  async function handleNotificationToggle(field) {
    if (!profile) return
    setNotifSaving(true)
    try {
      await updateNotifications({ [field]: !profile[field] })
      toast('Notification preferences saved')
    } catch (e) {
      toast(apiErrorText(e, 'Failed to save preferences'), 'error')
    } finally {
      setNotifSaving(false)
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    setPasswordError('')
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
      toast('Password updated')
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (e) {
      const detail = e.response?.data
      if (typeof detail === 'object' && detail?.current_password) {
        setPasswordError([].concat(detail.current_password)[0])
      } else if (typeof detail === 'object' && detail?.new_password) {
        setPasswordError([].concat(detail.new_password).join(' '))
      } else {
        setPasswordError(apiErrorText(e, 'Failed to change password'))
      }
    } finally {
      setPasswordSaving(false)
    }
  }

  // The server refuses to disable these (alerts/rules.py ALWAYS_ENABLED).
  const alwaysOn = (row) => ALWAYS_ENABLED.has(row.alert_type) && row.is_enabled

  const configColumns = [
    {
      key: 'alert_type',
      header: 'Alert type',
      render: (row) => <span className="font-medium text-zinc-100">{alertTypeTitle(row.alert_type)}</span>,
    },
    { key: 'zone', header: 'Applies to', render: (row) => row.zone_name || <span className="text-zinc-400">All zones</span> },
    {
      key: 'enabled',
      header: 'Enabled',
      render: (row) =>
        alwaysOn(row) ? (
          <span className="inline-flex items-center gap-1.5 text-xs text-zinc-400" title="Safety-critical: this alert cannot be turned off">
            <svg className="h-3.5 w-3.5 text-zinc-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <rect x="4" y="11" width="16" height="10" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
            Always on
          </span>
        ) : isAdmin ? (
          <Switch
            checked={row.is_enabled}
            disabled={togglingId === row.id}
            onChange={() => handleToggleEnabled(row)}
            label={`${alertTypeTitle(row.alert_type)} alerts`}
          />
        ) : (
          <Badge variant={row.is_enabled ? 'active' : 'offline'} dot>
            {row.is_enabled ? 'On' : 'Off'}
          </Badge>
        ),
    },
    {
      key: 'threshold',
      header: 'Threshold',
      render: (row) =>
        row.threshold_seconds ? (
          <span className="tabular-nums">{row.threshold_seconds} s</span>
        ) : (
          <span className="text-zinc-500">Immediate</span>
        ),
    },
    ...(isAdmin
      ? [
          {
            key: 'actions',
            header: <span className="sr-only">Actions</span>,
            cellClassName: 'text-right',
            render: (row) => (
              <Button variant="ghost" size="xs" onClick={() => openEditModal(row)}>
                <IconPencil className="h-3.5 w-3.5" />
                Edit
              </Button>
            ),
          },
        ]
      : []),
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Configure alerts, notifications, and your account" />

      <div className="flex gap-1 overflow-x-auto border-b border-zinc-800" role="tablist" aria-label="Settings sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            className={cn(
              '-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-amber-500',
              activeTab === tab.id
                ? 'border-amber-500 text-amber-300'
                : 'border-transparent text-zinc-400 hover:border-zinc-600 hover:text-zinc-200',
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error ? <Alert>{error}</Alert> : null}

      <div role="tabpanel" id={`panel-${activeTab}`} aria-labelledby={`tab-${activeTab}`}>
        {activeTab === 'alerts' ? (
          <Card>
            <CardHeader>
              <CardTitle>Alert rules</CardTitle>
              <CardDescription>
                {isAdmin
                  ? 'Turn alert types on or off and set how long a condition must last before it alerts. SOS, fire and gas are always on.'
                  : 'How alerts are configured on this site. Only an Admin can change them.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 [&>div]:rounded-none [&>div]:border-0">
              <DataTable
                columns={configColumns}
                data={alertConfigs}
                loading={loadingConfigs}
                emptyTitle="No alert configuration entries yet"
                rowKey={(row) => row.id}
                minWidthClass="min-w-[560px]"
              />
            </CardContent>
          </Card>
        ) : null}

        {activeTab === 'notifications' ? (
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>Control how you receive safety alerts. Changes save immediately.</CardDescription>
            </CardHeader>
            <CardContent>
              {loadingProfile ? (
                <p className="text-sm text-zinc-500">Loading preferences…</p>
              ) : (
                <div className="divide-y divide-zinc-800">
                  <SettingRow
                    title="Push notifications"
                    description="Receive mobile push alerts for critical incidents on the Site-Safe app"
                  >
                    <Switch
                      checked={!!profile?.notify_push}
                      disabled={notifSaving}
                      onChange={() => handleNotificationToggle('notify_push')}
                      label="Push notifications"
                    />
                  </SettingRow>
                  <SettingRow title="Email notifications" description="Receive alert summaries and escalations by email">
                    <Switch
                      checked={!!profile?.notify_email}
                      disabled={notifSaving}
                      onChange={() => handleNotificationToggle('notify_email')}
                      label="Email notifications"
                    />
                  </SettingRow>
                </div>
              )}
            </CardContent>
          </Card>
        ) : null}

        {activeTab === 'profile' ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Account</CardTitle>
                <CardDescription>Your name and role are set by an Admin.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {loadingProfile ? (
                  <p className="text-sm text-zinc-500">Loading profile…</p>
                ) : (
                  <>
                    <Input label="Name" value={profile?.full_name || 'Not set'} readOnly />
                    <Input label="Email" value={profile?.email || '—'} readOnly />
                    <div className="flex flex-col gap-1.5">
                      <span className="text-xs font-medium text-zinc-300">Role</span>
                      <span>
                        <Badge variant="primary">{profile?.role_label || ROLE_LABEL[role] || '—'}</Badge>
                      </span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Change password</CardTitle>
                <CardDescription>Use at least 8 characters, and not one you use elsewhere.</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={handlePasswordSubmit}>
                  <Input
                    label="Current password"
                    type="password"
                    autoComplete="current-password"
                    value={passwordForm.current_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, current_password: e.target.value }))}
                    required
                  />
                  <Input
                    label="New password"
                    type="password"
                    autoComplete="new-password"
                    value={passwordForm.new_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                    minLength={8}
                    required
                  />
                  <Input
                    label="Confirm new password"
                    type="password"
                    autoComplete="new-password"
                    value={passwordForm.confirm_password}
                    onChange={(e) => setPasswordForm((f) => ({ ...f, confirm_password: e.target.value }))}
                    minLength={8}
                    required
                  />
                  {passwordError ? <Alert>{passwordError}</Alert> : null}
                  <Button type="submit" variant="primary" loading={passwordSaving}>
                    Update password
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>

      <Drawer
        open={!!editingConfig}
        onClose={closeEditModal}
        title={editingConfig ? `${alertTypeTitle(editingConfig.alert_type)} rule` : 'Edit alert rule'}
        description={editingConfig ? `Applies to ${editingConfig.zone_name || 'all zones'}` : ''}
        footer={
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={closeEditModal}>
              Cancel
            </Button>
            <Button type="submit" form="alert-config-form" variant="primary" loading={savingConfig}>
              Save rule
            </Button>
          </div>
        }
      >
        <form id="alert-config-form" className="space-y-5" onSubmit={saveConfigEdit}>
          {editingConfig && alwaysOn(editingConfig) ? (
            <Alert tone="info">This alert is safety-critical and always on. Only its threshold can be changed.</Alert>
          ) : (
            <SettingRow title="Enabled" description="When off, this condition is not reported as an alert.">
              <Switch
                checked={editDraft.is_enabled}
                onChange={(val) => setEditDraft((d) => ({ ...d, is_enabled: val }))}
                label="Enabled"
              />
            </SettingRow>
          )}
          <Input
            label="Threshold (seconds)"
            type="number"
            min={0}
            value={editDraft.threshold_seconds}
            onChange={(e) => setEditDraft((d) => ({ ...d, threshold_seconds: e.target.value }))}
            hint="How long the condition must last before an alert is raised. 0 alerts immediately."
          />
          {configError ? <Alert>{configError}</Alert> : null}
        </form>
      </Drawer>
    </div>
  )
}

function SettingRow({ title, description, children }) {
  return (
    <div className="flex items-center justify-between gap-6 py-3.5 first:pt-0 last:pb-0">
      <div>
        <p className="text-sm font-medium text-zinc-100">{title}</p>
        <p className="mt-0.5 text-xs text-zinc-500">{description}</p>
      </div>
      {children}
    </div>
  )
}
