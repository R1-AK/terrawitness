import type { Incident } from '../../lib/types'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

const VIOLATION_LABEL: Record<string, string> = {
  illegal_clearing:       'Illegal clearing',
  tailings_discharge:     'Tailings discharge',
  unauthorized_expansion: 'Unauthorized expansion',
  river_contamination:    'River contamination',
  protected_area_breach:  'Protected area breach',
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })
}

interface Props {
  incidents: Incident[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export default function IncidentFeed({ incidents, selectedId, onSelect }: Props) {
  const sorted = [...incidents].sort(
    (a, b) => new Date(b.post_date).getTime() - new Date(a.post_date).getTime()
  )

  if (sorted.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>No cases in selected period</span>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {sorted.map((inc, i) => {
        const color = SEV_COLOR[inc.severity]
        const isSelected = inc.id === selectedId

        return (
          <button
            key={inc.id}
            onClick={() => onSelect(inc.id)}
            className="feed-item-enter"
            style={{
              animationDelay: `${i * 25}ms`,
              width: '100%', textAlign: 'left',
              display: 'flex', alignItems: 'flex-start', gap: '10px',
              border: 'none', cursor: 'pointer',
              padding: '10px 14px',
              borderBottom: '1px solid var(--border)',
              background: isSelected ? 'var(--surface-2)' : 'transparent',
              transition: 'background 0.1s',
            }}
            onMouseEnter={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'var(--surface-2)'
            }}
            onMouseLeave={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'
            }}
          >
            {/* Severity dot */}
            <span style={{
              width: '7px', height: '7px', borderRadius: '50%',
              background: color, flexShrink: 0, marginTop: '4px',
            }} />

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '6px', marginBottom: '2px' }}>
                <span style={{
                  fontSize: '12px', fontWeight: 600, color: 'var(--text-1)',
                  lineHeight: 1.3, letterSpacing: '-0.01em',
                }}>
                  {VIOLATION_LABEL[inc.violation_type]}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                  {formatDate(inc.source_date)}
                </span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
                {inc.location.desa}, {inc.location.kabupaten}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
