import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Incident } from '../../lib/types'

const SEV_COLOR: Record<string, string> = {
  critical: '#F43F5E',
  high:     '#FB923C',
  medium:   '#FACC15',
  low:      '#34D399',
}

const STATUS_OPACITY: Record<string, number> = {
  incoming:   0.35,
  geoparsing: 0.5,
  satellite:  0.65,
  landuse:    0.8,
  verified:   1,
  routed:     1,
}

interface LeaseData {
  lease_name:   string
  komoditas:    string
  kegiatan:     string
  luas_ha:      number
  centroid:     [number, number]
  pit_centroid: [number, number]
  polygon:      [number, number][][]
}

interface SignalData {
  signal_point: [number, number]   // [lat, lng]
  signal_type:  string             // teluk | coastal | river | pit | pit_fallback
  label:        string
}

type LeaseMap   = Record<string, LeaseData>
type SignalMap  = Record<string, SignalData>

interface Props {
  incidents: Incident[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export default function IncidentMap({ incidents, selectedId, onSelect }: Props) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map          = useRef<L.Map | null>(null)
  const markers      = useRef<Record<string, L.CircleMarker>>({})
  const pulseMarkers = useRef<L.Marker[]>([])
  const leaseLayer   = useRef<L.Polygon | null>(null)
  const leaseLabel   = useRef<L.Marker | null>(null)

  const [leases,  setLeases]  = useState<LeaseMap>({})
  const [signals, setSignals] = useState<SignalMap>({})

  // Load lease polygons and signal points
  useEffect(() => {
    fetch('/lease_polygons.json')
      .then(r => r.json())
      .then((data: LeaseMap) => setLeases(data))
      .catch(() => {})
    fetch('/incident_signals.json')
      .then(r => r.json())
      .then((data: SignalMap) => setSignals(data))
      .catch(() => {})
  }, [])

  // Init map once
  useEffect(() => {
    if (!mapContainer.current || map.current) return

    map.current = L.map(mapContainer.current, {
      center: [-1.5, 124.5],
      zoom: 6,
      zoomControl: false,
    })

    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { attribution: 'Esri, Maxar, Earthstar Geographics', maxZoom: 19 }
    ).addTo(map.current)

    L.control.zoom({ position: 'bottomright' }).addTo(map.current)

    return () => { map.current?.remove(); map.current = null }
  }, [])

  // Sync markers — runs again when leases load
  useEffect(() => {
    if (!map.current) return

    Object.values(markers.current).forEach(m => m.remove())
    pulseMarkers.current.forEach(m => m.remove())
    markers.current = {}
    pulseMarkers.current = []

    incidents.forEach(inc => {
      const color   = SEV_COLOR[inc.severity]
      const opacity = STATUS_OPACITY[inc.status]
      const isSel   = inc.id === selectedId
      const lease   = leases[inc.id]

      // Priority: OSM-derived signal point (teluk/river/coastal) > BSI pit > polygon centroid > community coords
      const sig = signals[inc.id]
      const pt  = sig?.signal_point ?? lease?.pit_centroid ?? lease?.centroid
      const lat = pt ? pt[0] : inc.location.lat
      const lng = pt ? pt[1] : inc.location.lng

      const marker = L.circleMarker([lat, lng], {
        radius:      isSel ? 11 : 8,
        fillColor:   color,
        fillOpacity: opacity,
        color:       isSel ? '#ffffff' : 'rgba(255,255,255,0.25)',
        weight:      isSel ? 2 : 1,
        bubblingMouseEvents: false,
      }).addTo(map.current!)

      marker.on('click', () => onSelect(inc.id))
      markers.current[inc.id] = marker

      // Pulse ring — all incidents
      if (true) {
        const r = isSel ? 11 : 8
        const pulse = L.divIcon({
          className: '',
          html: `<div style="
            width:${r * 4}px;height:${r * 4}px;
            margin-left:-${r * 2}px;margin-top:-${r * 2}px;
            border-radius:50%;
            background:${color};
            opacity:0;
            animation:pulseRing 2.4s ease-out infinite;
          "></div>`,
          iconSize: [0, 0],
        })
        const pm = L.marker([lat, lng], {
          icon: pulse, interactive: false, zIndexOffset: -100,
        }).addTo(map.current!)
        pulseMarkers.current.push(pm)
      }
    })
  }, [incidents, selectedId, onSelect, leases, signals])

  // Lease polygon overlay on selection
  useEffect(() => {
    if (!map.current) return

    leaseLayer.current?.remove()
    leaseLabel.current?.remove()
    leaseLayer.current = null
    leaseLabel.current = null

    if (!selectedId) return
    const inc   = incidents.find(i => i.id === selectedId)
    const lease = leases[selectedId]
    if (!inc) return

    const scoreColor = inc.change_score > 0.75 ? '#F43F5E'
                     : inc.change_score > 0.45  ? '#FB923C'
                     : '#34D399'

    // Only draw lease boundary when the report names a specific operator
    const hasNamedOperator = inc.concession_holder != null && /\bPT\b/.test(inc.concession_holder)

    if (lease?.polygon?.length && hasNamedOperator) {
      // Polygon coords are [lng, lat] — Leaflet needs [lat, lng]
      const latlngs = lease.polygon[0].map(([lng, lat]) => [lat, lng] as [number, number])

      leaseLayer.current = L.polygon(latlngs, {
        color:       '#22D3EE',
        weight:      2,
        opacity:     0.85,
        fillColor:   scoreColor,
        fillOpacity: 0.15,
        dashArray:   '8 5',
        interactive: false,
      }).addTo(map.current)

      // Lease name label at centroid
      const labelIcon = L.divIcon({
        className: '',
        html: `<div style="
          white-space:nowrap;
          font-family:'DM Mono',monospace;
          font-size:10px;
          color:#22D3EE;
          pointer-events:none;
          transform:translateX(-50%);
          text-shadow:0 1px 3px rgba(0,0,0,0.9);
        ">${lease.lease_name}</div>`,
        iconSize: [0, 0],
      })
      leaseLabel.current = L.marker(
        [lease.centroid[0], lease.centroid[1]],
        { icon: labelIcon, interactive: false, zIndexOffset: 500 }
      ).addTo(map.current)

      // Fly to fit the actual mining lease extent
      map.current.flyToBounds(
        leaseLayer.current.getBounds(),
        { padding: [60, 60], duration: 1.3, maxZoom: 13 }
      )
    } else {
      // No named operator or no polygon — fly to signal point
      const sig = signals[selectedId]
      const pt  = sig?.signal_point ?? (lease ? [lease.pit_centroid[0], lease.pit_centroid[1]] : null)
      const flyLat = pt ? pt[0] : inc.location.lat
      const flyLng = pt ? pt[1] : inc.location.lng
      map.current.flyTo([flyLat, flyLng], 11, { duration: 1.2 })
    }
  }, [selectedId, incidents, leases, signals])

  return (
    <div
      ref={mapContainer}
      style={{ width: '100%', height: '100%', background: '#05080F' }}
    />
  )
}
