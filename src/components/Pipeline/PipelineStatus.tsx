import { Radio, MapPin, Satellite, Layers, FileCheck } from 'lucide-react'

const STAGES = [
  { key: 'detect',    icon: <Radio size={10} />,      label: 'Detect' },
  { key: 'geoparse',  icon: <MapPin size={10} />,     label: 'Geoparse' },
  { key: 'satellite', icon: <Satellite size={10} />,  label: 'Satellite' },
  { key: 'landuse',   icon: <Layers size={10} />,     label: 'Land Use' },
  { key: 'evidence',  icon: <FileCheck size={10} />,  label: 'Evidence' },
]

export default function PipelineStatus() {
  return (
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
  )
}
