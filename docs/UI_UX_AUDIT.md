# Web portal UI/UX audit — 4 November 2026

Every page of the web portal (`frontend/`) was used as an Admin at 1440×900 and at phone width (375 px), with the backend running against the local database. This file lists what was found and what was done about it. Items not fixed are in [PENDING_FOR_YOU.md](PENDING_FOR_YOU.md).

## Critical: options that did not work

| # | Finding | Cause | Fix |
|---|---|---|---|
| 1 | Resolve, Edit, Add, Register, Delete, the alert-rule switches and the whole **Cameras** page were missing. The top bar showed the role as "…". | The portal granted the role only when the email typed at login exactly matched the account the server returned. A different capital letter at login, or a token kept from another account, left the user with no role. | The signed-in identity (email, name, role) now comes from the server's profile. The role is still cleared on every login and logout, so it never carries over to another account (`context/AuthContext.jsx`). |
| 2 | Alert-rule switches drew their knob outside the track. | The knob was absolutely positioned without a left edge. | New shared `Switch` component (`components/ui/Switch.jsx`). |
| 3 | Resolving one incident turned the whole incident table and alert feed into a loading skeleton. | Every resolve re-fetched the list with the loading flag on. | Refreshes after a resolve or a live resync are now quiet (`hooks/useAlerts.js`). |
| 4 | A failed resolve, report download or zone delete showed nothing, or a browser `alert()` box. | Errors were not caught, or used `window.alert`. | In-app notifications for every save, resolve, delete and failure (`context/FeedbackContext.jsx`). |
| 5 | The Zones map rendered as scattered grey tiles. | Leaflet measured its container before the layout settled. | The map re-measures whenever its card changes size (`components/map/SiteMap.jsx`). |
| 6 | Scrolling the page over any map zoomed the map instead. | Wheel zoom was always on. | Wheel zoom turns on after a click on the map and off when the pointer leaves it. |
| 7 | Vest Management squeezed the table into half the width beside an empty "Select a vest" panel; the Actions column was cut off. | Fixed two-column grid. | Full-width table; clicking a row (or **Details**) opens a slide-over with live telemetry and assignment. |
| 8 | The site was unusable on a phone: the 240 px sidebar never collapsed. | No mobile layout. | Off-canvas navigation opened from a menu button; no horizontal page scroll at 375 px. |
| 9 | The login page said "Invalid email or password" when the server was unreachable. | One message for every failure. | Separate messages for wrong credentials, a server error and no connection. |

## Navigation

| # | Finding | Fix |
|---|---|---|
| 10 | The top bar repeated "Site-Safe" and never said which page you were on. | Breadcrumb with the page name; the browser tab title follows the page. |
| 11 | The account chip in the top bar did nothing; Sign out and the email were duplicated at the bottom of the sidebar. | Account menu with profile, notification settings and **Sign out**. The sidebar footer now shows only the live-update status and the collapse control. |
| 12 | The bell, the Open Alerts figure and "View all" in the alert feed went to the full log, not the open alerts. | They open **Incidents** filtered to open alerts (`/incidents?status=open`). |
| 13 | Settings tabs could not be linked to. | `/settings?tab=profile` and `?tab=notifications`; the account menu uses them. |
| 14 | The collapsed sidebar had no labels or open-incident indicator, and forgot its state on reload. | Hover labels, a red dot for open incidents, and the collapsed state is remembered. |
| 15 | Viewers saw **Reports** in the menu but only a one-line refusal on the page. | Reports is hidden for Viewers, like Cameras; a direct visit shows a proper explanation. |
| 16 | No way to skip the navigation by keyboard. | "Skip to content" link. |

## Buttons, forms and feedback

| # | Finding | Fix |
|---|---|---|
| 17 | Zone rows had solid red **Delete** buttons; other row actions were plain text links ("Timeline", "Edit", "View"). | One button set: primary, secondary, ghost, a quiet `danger` for row actions and a solid `destructive` only inside a confirmation. Row actions carry icons. |
| 18 | Busy buttons showed "…" or changed their label. | Buttons take a `loading` state with a spinner and keep their size. |
| 19 | Destructive actions used the browser's `confirm()` box (zone delete, permit revoke, camera unplace, danger-area delete, badge reissue). | A styled confirmation dialog that says what will happen; Cancel has the focus and Escape cancels. The zone-delete wording was checked against the data model (alert rules and permits for that zone are removed, incidents are kept). |
| 20 | Slide-over panels could not be closed with Escape, did not move focus, and used a "✕" character. | Escape closes, focus moves in and back, proper close icon; selects are not auto-focused, because the vest assignment saves on change. |
| 21 | Filter chips on Incidents did not show their state except by colour; there was no status filter and no way to clear filters. | Chips show a tick and `aria-pressed`; All / Open / Resolved control with counts; **Clear filters**; result count. |
| 22 | Clickable incident rows gave no hint that they expand, and could not be opened from the keyboard. | Chevron column; rows are focusable and open with Enter or Space. |
| 23 | Native date pickers, checkboxes and scrollbars rendered light on the dark page. | `color-scheme: dark` and an amber accent colour. |
| 24 | Alert rules for SOS, fire and gas showed a bare "On" that looked like a broken switch. | "Always on" with a lock and an explanation. |
| 25 | Reports had no quick date ranges and two loose radio buttons for the format. | Last 7 / 30 / 90 days; PDF / Word as a segmented control; download buttons with progress and error handling. |

## Visual design

| # | Finding | Fix |
|---|---|---|
| 26 | KPI cards each had a different coloured left border and were not clickable. | Uniform cards with an icon chip; Workers on site, Open alerts and Alerts today link to their pages. Flat all-zero sparklines are hidden. |
| 27 | Worker names wrapped onto two lines because the status badge shared their row. | Card rebuilt: name and trade on one line, status badge with a dot, actions in a footer. |
| 28 | Alert types were shown in capitals ("PPE VIOLATION"); timestamps older than a day showed only a time ("7 d ago · 15:11"). | Title case that keeps acronyms ("PPE Violation"); older timestamps include the date. |
| 29 | The bright OpenStreetMap tiles clashed with the dark interface. | Tiles are darkened in CSS; zones, vests and cameras keep their true colours. Map controls are styled to match. A legend explains the colours on the Zones map. |
| 30 | Page headers, empty states and error banners were written out differently on each page. | Shared `PageHeader`, `EmptyState` and `Alert` components. |
| 31 | The Settings icon was a sun, and icons used mixed stroke styles. | One icon set with consistent geometry (`components/ui/icons.jsx`). |

## Checked and left as they were

- Page names and the menu order, so the report and the demo script still match.
- The Name field in Settings stays read-only: the server deliberately does not let users rename themselves.
- Production build and lint pass (`npm run build`, `npm run lint`). The existing large-bundle warning from Vite is unchanged.
