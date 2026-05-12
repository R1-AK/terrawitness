import { Radio, MapPin, Satellite, Layers, FileCheck } from 'lucide-react'

const STAGES = [
  { key: 'detect',    icon: <Radio size={10} />,      label: 'Detect' },
  { key: 'geoparse',  icon: <MapPin size={10} />,     label: 'Geoparse' },
  { key: 'satellite', icon: <Satellite size={10} />,  label: 'Satellite' },
  { key: 'landuse',   icon: <Layers size={10} />,     label: 'Land Use' },
  { key: 'evidence',  icon: <FileCheck size={10} />,  label: 'Evidence' },
]

const SOURCES = [
  { label: 'RSS',       active: true  },
  { label: 'X/Twitter', active: false },
]

export default function PipelineStatus() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

      {/* Pipeline stages */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
        {STAGES.map((stage, i) => (
          <div key={stage.key} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '3px 8px', borderRadius: '4px',
              color: 'var(--text-2)',
              fontSize: '10px', fontWeight: 500,
              letterSpacing: '0.04em',
            }}>
              {stage.icon}
              <span style={{ display: 'none' }} className="sm:inline">{stage.label}</span>
            </div>
            {i < STAGES.length - 1 && (
              <div style={{ width: '12px', height: '1px', background: 'var(--border-2)' }} />
            )}
          </div>
        ))}
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />

      {/* Data source badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        {SOURCES.map(s => (
          <div key={s.label} style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '2px 7px', borderRadius: '4px',
            fontSize: '10px', fontWeight: 600,
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.04em',
            background: s.active ? 'rgba(34,211,238,0.08)' : 'rgba(255,255,255,0.04)',
            border: `1px solid ${s.active ? 'rgba(34,211,238,0.25)' : 'var(--border)'}`,
            color: s.active ? 'var(--accent)' : 'var(--text-3)',
          }}>
            <span style={{
              width: '5px', height: '5px', borderRadius: '50%',
              background: s.active ? 'var(--accent)' : 'var(--text-3)',
              display: 'inline-block', flexShrink: 0,
            }} />
            {s.label}
            {!s.active && (
              <span style={{ fontSize: '9px', color: 'var(--text-3)', marginLeft: '1px' }}>planned</span>
            )}
          </div>
        ))}
      </div>

    </div>
  )
}
