import type { Incident } from '../../lib/types'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })
}

interface Props {
  incidents:  Incident[]
  selectedId: string | null
  onSelect:   (id: string) => void
}

export default function IncidentFeed({ incidents, selectedId, onSelect }: Props) {
  const sorted = [...incidents].sort(
    (a, b) => new Date(b.post_date).getTime() - new Date(a.post_date).getTime()
  )

  if (sorted.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '13px', color: 'var(--text-3)' }}>No cases in selected period</span>
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
              display: 'flex', alignItems: 'flex-start', gap: '11px',
              border: 'none', cursor: 'pointer',
              padding: '12px 14px',
              borderLeft: `3px solid ${isSelected ? color : 'transparent'}`,
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
              width: '8px', height: '8px', borderRadius: '50%',
              background: color, flexShrink: 0, marginTop: '5px',
            }} />

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '8px', marginBottom: '3px' }}>
                <span style={{
                  fontSize: '14px', fontWeight: 700, color: 'var(--text-1)',
                  lineHeight: 1.25, letterSpacing: '-0.01em',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {inc.location.desa}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                  {formatDate(inc.source_date)}
                </span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-2)' }}>
                {inc.location.kabupaten}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
