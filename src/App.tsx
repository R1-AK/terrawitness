import { useState, useEffect } from 'react'
import IncidentMap from './components/Map/IncidentMap'
import StatsPanel from './components/Dashboard/StatsPanel'
import IncidentFeed from './components/Dashboard/IncidentFeed'
import TimelineFilter from './components/Dashboard/TimelineFilter'
import EvidenceCard from './components/Report/EvidenceCard'
import { MOCK_INCIDENTS, MOCK_STATS } from './lib/mockData'
import type { Incident, Stats } from './lib/types'

export default function App() {
  const [selectedId, setSelectedId]     = useState<string | null>(null)
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [liveIncidents, setLiveIncidents] = useState<Incident[]>([])

  useEffect(() => {
    fetch('/incidents_live.json')
      .then(r => r.json())
      .then((data: Incident[]) => {
        if (Array.isArray(data) && data.length > 0) setLiveIncidents(data)
      })
      .catch(() => {})
  }, [])

  const allIncidents = [
    ...MOCK_INCIDENTS,
    ...liveIncidents.filter(l => !MOCK_INCIDENTS.find(m => m.id === l.id)),
  ]

  const filteredIncidents = selectedYear
    ? allIncidents.filter(i => new Date(i.source_date).getFullYear() === selectedYear)
    : allIncidents

  const selectedIncident: Incident | null =
    filteredIncidents.find(i => i.id === selectedId) ?? null

  const stats: Stats = {
    ...MOCK_STATS,
    total_incidents:    allIncidents.length,
    violations_flagged: allIncidents.filter(i => i.violation_flag).length,
    verified:           allIncidents.filter(i => i.status === 'verified' || i.status === 'routed').length,
  }

  const handleSelect = (id: string) => setSelectedId(prev => prev === id ? null : id)
  const handleYearSelect = (year: number | null) => { setSelectedYear(year); setSelectedId(null) }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      {/* Header */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: '44px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        flexShrink: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '24px', height: '24px', borderRadius: '5px',
            background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <span style={{ color: '#fff', fontWeight: 800, fontSize: '10px', letterSpacing: '-0.02em', fontFamily: 'var(--font-mono)' }}>TW</span>
          </div>
          <span style={{ color: 'var(--text-1)', fontWeight: 700, fontSize: '14px', letterSpacing: '-0.02em' }}>TerraWitness</span>
          <span style={{ color: 'var(--text-3)', fontSize: '12px' }}>Civic Satellite Verification</span>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '2px 7px', borderRadius: '3px',
            background: 'rgba(196,28,28,0.07)', border: '1px solid rgba(196,28,28,0.15)',
          }}>
            <span className="live-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--critical)', display: 'inline-block' }} />
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--critical)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>LIVE</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Source badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>Sources:</span>
            <span style={{
              fontSize: '10px', fontWeight: 600, padding: '2px 7px', borderRadius: '3px',
              background: 'rgba(14,116,144,0.08)', border: '1px solid rgba(14,116,144,0.2)',
              color: 'var(--accent)',
            }}>RSS active</span>
            <span style={{
              fontSize: '10px', fontWeight: 600, padding: '2px 7px', borderRadius: '3px',
              background: 'var(--surface-2)', border: '1px solid var(--border)',
              color: 'var(--text-3)',
            }}>X/Twitter planned</span>
          </div>

          <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />

          <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
            Maluku Utara · Sulawesi Tenggara
          </span>
        </div>
      </header>

      {/* Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Left sidebar */}
        <aside style={{
          width: '300px', flexShrink: 0,
          display: 'flex', flexDirection: 'column',
          background: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          overflow: 'hidden',
        }}>
          <StatsPanel stats={stats} />

          <TimelineFilter
            incidents={MOCK_INCIDENTS}
            selectedYear={selectedYear}
            onYearSelect={handleYearSelect}
          />

          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '8px 14px', borderBottom: '1px solid var(--border)', flexShrink: 0,
          }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-2)' }}>
              {filteredIncidents.length} cases
            </span>
            {selectedYear && (
              <button onClick={() => handleYearSelect(null)} style={{
                fontSize: '11px', color: 'var(--accent)', background: 'none',
                border: 'none', cursor: 'pointer',
              }}>
                Clear filter ×
              </button>
            )}
          </div>

          <IncidentFeed
            incidents={filteredIncidents}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
        </aside>

        {/* Map */}
        <main style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <IncidentMap
            incidents={filteredIncidents}
            selectedId={selectedId}
            onSelect={handleSelect}
          />

          <div style={{
            position: 'absolute', bottom: '10px', left: '10px',
            fontSize: '10px', color: 'rgba(0,0,0,0.4)',
            background: 'rgba(255,255,255,0.75)', padding: '3px 8px', borderRadius: '4px',
            fontFamily: 'var(--font-mono)', pointerEvents: 'none',
            backdropFilter: 'blur(4px)',
          }}>
            Esri World Imagery · TerraWitness
          </div>

          {!selectedId && (
            <div style={{
              position: 'absolute', top: '14px', left: '50%', transform: 'translateX(-50%)',
              pointerEvents: 'none',
            }}>
              <div style={{
                background: 'rgba(255,255,255,0.9)', border: '1px solid var(--border)',
                color: 'var(--text-2)', fontSize: '12px',
                padding: '6px 16px', borderRadius: '20px',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
              }}>
                Select a case to view evidence
              </div>
            </div>
          )}
        </main>

        {/* Evidence panel */}
        {selectedIncident && (
          <aside className="panel-enter" style={{
            width: '360px', flexShrink: 0,
            display: 'flex', flexDirection: 'column',
            background: 'var(--surface)',
            borderLeft: '1px solid var(--border)',
            overflow: 'hidden',
          }}>
            <EvidenceCard incident={selectedIncident} onClose={() => setSelectedId(null)} />
          </aside>
        )}
      </div>

      {/* Footer */}
      <footer style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: '30px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: '11px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
          TerraWitness · Falling Walls Lab Yogyakarta 2026
        </span>
        <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
          Monash University Mining Spatial Data Intelligence Lab
        </span>
      </footer>
    </div>
  )
}
