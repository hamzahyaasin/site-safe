import {
  IconAlertTriangle,
  IconCamera,
  IconGrid,
  IconMap,
  IconReport,
  IconSettings,
  IconUsers,
  IconVest,
} from '../ui/icons.jsx'

/** Sidebar sections. ``operatorsOnly`` items need the Safety Officer or Admin role. */
export const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [{ to: '/', label: 'Dashboard', icon: IconGrid, end: true }],
  },
  {
    label: 'Operations',
    items: [
      { to: '/workers', label: 'Workers', icon: IconUsers },
      { to: '/incidents', label: 'Incidents', icon: IconAlertTriangle, badgeKey: 'incidents' },
      { to: '/vests', label: 'Vest Management', icon: IconVest },
      { to: '/cameras', label: 'Cameras', icon: IconCamera, operatorsOnly: true },
    ],
  },
  {
    label: 'Site',
    items: [
      { to: '/zones', label: 'Zones', icon: IconMap },
      { to: '/reports', label: 'Reports', icon: IconReport, operatorsOnly: true },
      { to: '/settings', label: 'Settings', icon: IconSettings },
    ],
  },
]

const TITLES = {
  '/': 'Dashboard',
  '/workers': 'Workers',
  '/incidents': 'Incidents',
  '/vests': 'Vest Management',
  '/cameras': 'Cameras',
  '/zones': 'Zones',
  '/reports': 'Reports',
  '/settings': 'Settings',
}

/** The page name for the top bar and the browser tab. */
export function pageTitle(pathname) {
  return TITLES[pathname] ?? TITLES[`/${pathname.split('/')[1]}`] ?? 'Site-Safe'
}
