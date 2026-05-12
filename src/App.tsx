import { useState } from 'react'
import IncidentMap from './components/Map/IncidentMap'
import StatsPanel from './components/Dashboard/StatsPanel'
import IncidentFeed from './components/Dashboard/IncidentFeed'
import TimelineFilter from './components/Dashboard/TimelineFilter'
import EvidenceCard from './components/Report/EvidenceCard'
import PipelineStatus from './components/Pipeline/PipelineStatus'
import { MOCK_INCIDENTS, MOCK_STATS } from './lib/mockData'
import type { Incident } from './lib/types'

export default function App() {
  const [selectedId, setSelectedId]     = useState<string | null>(null)
  const [selectedYear, setSelectedYear] = useState<number | null>(null)

  const filteredIncidents = selectedYear
    ? MOCK_INCIDENTS.filter(i => new Date(i.source_date).getFullYear() === selectedYear)
    : MOCK_INCIDENTS

  const selectedIncident: Incident | null =
    filteredIncidents.find(i => i.id === selectedId) ?? null

  const handleSelect = (id: string) => setSelectedId(prev => prev === id ? null : id)

  const handleYearSelect = (year: number | null) => {
    setSelectedYear(year)
    setSelectedId(null)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        height: '48px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        flexShrink: 0,
        zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px', height: '28px', borderRadius: '6px',
            background: 'linear-gradient(135deg, #22D3EE 0%, #0EA5E9 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ color: '#04111F', fontWeight: 800, fontSize: '11px', letterSpacing: '-0.02em', fontFamily: 'var(--font-mono)' }}>TW</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-1)', fontWeight: 700, fontSize: '14px', letterSpacing: '-0.02em' }}>TerraWitness</span>
            <span style={{ color: 'var(--text-3)', fontSize: '12px', marginLeft: '8px' }}>Civic Satellite Verification Engine</span>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            padding: '3px 8px', borderRadius: '4px',
            background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.18)',
            marginLeft: '4px',
          }}>
            <span className="live-dot" style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--critical)', display: 'inline-block' }} />
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--critical)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>LIVE</span>
          </div>
        </div>

        {/* Pipeline */}
        <PipelineStatus />

        {/* Region */}
        <div style={{ fontSize: '11px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textAlign: 'right' }}>
          <span style={{ color: 'var(--text-2)' }}>East Indonesia</span>
          <span style={{ margin: '0 6px', color: 'var(--text-3)' }}>·</span>
          <span>Maluku Utara — Sulawesi Tenggara</span>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Left sidebar */}
        <aside style={{
          width: '320px',
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          overflow: 'hidden',
        }}>
          {/* Dataset note */}
          <div style={{
            padding: '8px 16px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--accent-glow)',
          }}>
            <p style={{ fontSize: '11px', color: 'var(--text-2)', lineHeight: 1.5 }}>
              Demo dataset reconstructed from documented nickel-mining incidents
              in Maluku Utara and Sulawesi Tenggara.
            </p>
          </div>

          <StatsPanel stats={MOCK_STATS} />

          <TimelineFilter
            incidents={MOCK_INCIDENTS}
            selectedYear={selectedYear}
            onYearSelect={handleYearSelect}
          />

          {/* Feed header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 16px',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
              Signal feed
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
              {filteredIncidents.length} / {MOCK_INCIDENTS.length}
            </span>
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

          {/* Map label */}
          <div style={{
            position: 'absolute', bottom: '12px', left: '12px',
            fontSize: '10px', color: 'rgba(255,255,255,0.4)',
            background: 'rgba(8,11,17,0.65)', padding: '4px 8px', borderRadius: '4px',
            fontFamily: 'var(--font-mono)', pointerEvents: 'none',
            backdropFilter: 'blur(4px)',
          }}>
            Esri World Imagery · TerraWitness analysis layer
          </div>

          {!selectedId && (
            <div style={{
              position: 'absolute', top: '16px', left: '50%', transform: 'translateX(-50%)',
              pointerEvents: 'none',
            }}>
              <div style={{
                background: 'rgba(13,17,23,0.85)', border: '1px solid var(--border-2)',
                color: 'var(--text-2)', fontSize: '12px',
                padding: '8px 16px', borderRadius: '20px',
                backdropFilter: 'blur(8px)',
              }}>
                Select an incident to view evidence
              </div>
            </div>
          )}
        </main>

        {/* Right panel */}
        {selectedIncident && (
          <aside
            className="panel-enter"
            style={{
              width: '380px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--surface)',
              borderLeft: '1px solid var(--border)',
              overflow: 'hidden',
            }}
          >
            <EvidenceCard incident={selectedIncident} onClose={() => setSelectedId(null)} />
          </aside>
        )}
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: '32px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: '11px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
          TerraWitness MVP · Falling Walls Lab Yogyakarta 2026
        </span>
        <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
          Monash University Mining Spatial Data Intelligence Lab
        </span>
      </footer>
    </div>
  )
}
