import { Link } from 'react-router-dom'
import { cameraStatus, useCameraMap } from '../../hooks/useCameraMap.js'
import { useGasMonitors } from '../../hooks/useGasMonitors.js'
import { useVests } from '../../hooks/useVests.js'
import { useZones } from '../../hooks/useZones.js'
import SiteMap from '../map/SiteMap.jsx'
import Card, { CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card.jsx'

/** The live site map on the dashboard: zones with head counts, vests, gas monitors, and cameras with their alerts (FR-33). */
export default function SiteMapCard() {
  const { zones } = useZones()
  const { vests } = useVests()
  const { cameras, alerting } = useCameraMap()
  const { monitors } = useGasMonitors()
  const gasZones = [...new Set(monitors.filter((m) => m.gas_over_limit).map((m) => m.zone_name || m.monitor_id))]
  const placed = cameras.filter((c) => c.placement)
  const counts = { live: 0, offline: 0, alerting: 0 }
  for (const c of placed) counts[cameraStatus(c, alerting)] += 1
  const unplaced = cameras.length - placed.length

  return (
    <Card className="col-span-12">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle>Site Map</CardTitle>
          <CardDescription>
            Zones with live head counts, vests, gas monitors (rings), and cameras with what they cover. A camera turns
            red for a minute after it raises an alert; click one for its live picture and alerts. A zone with gas over
            the limit is outlined in red.
          </CardDescription>
        </div>
        <p className="flex flex-wrap items-center gap-3 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            {counts.live} live
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-zinc-500" />
            {counts.offline} offline
          </span>
          {counts.alerting ? (
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              {counts.alerting} alerting
            </span>
          ) : null}
          {gasZones.length ? (
            <span className="flex items-center gap-1.5 font-semibold text-red-400">
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              Gas: {gasZones.join(', ')}
            </span>
          ) : null}
          {unplaced ? (
            <Link to="/zones" className="text-amber-400 hover:text-amber-300">
              {unplaced} not on the map
            </Link>
          ) : null}
        </p>
      </CardHeader>
      <CardContent>
        <SiteMap zones={zones} vests={vests} cameras={cameras} alerting={alerting} gasMonitors={monitors} height={400} />
      </CardContent>
    </Card>
  )
}
