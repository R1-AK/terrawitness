import type { Incident } from '../../lib/types'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

const STATUS_LABEL: Record<string, string> = {
  incoming:   'Incoming',
  geoparsing: 'Geoparsing',
  satellite:  'Satellite',
  landuse:    'Land Use',
  verified:   'Verified',
  routed:     'Routed',
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
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
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
        <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>No incidents in selected period</span>
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
              animationDelay: `${i * 30}ms`,
              width: '100%', textAlign: 'left',
              display: 'block', border: 'none', cursor: 'pointer',
              padding: '12px 16px 12px 13px',
              borderLeft: `3px solid ${isSelected ? color : 'transparent'}`,
              borderBottom: '1px solid var(--border)',
              background: isSelected ? `${color}08` : 'transparent',
              transition: 'background 0.12s, border-color 0.12s',
            }}
            onMouseEnter={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'var(--surface-2)'
            }}
            onMouseLeave={e => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'
            }}
          >
            {/* Top row: violation type + date */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.2 }}>
                {VIOLATION_LABEL[inc.violation_type]}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                {formatDate(inc.source_date)}
              </span>
            </div>

            {/* Location */}
            <div style={{ fontSize: '11px', color: 'var(--text-2)', marginBottom: '6px' }}>
              {inc.location.desa}, {inc.location.kabupaten}
            </div>

            {/* Excerpt */}
            <p style={{
              fontSize: '11px', color: 'var(--text-2)', lineHeight: 1.55,
              display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
              overflow: 'hidden', marginBottom: '8px',
            }}>
              {inc.post_text}
            </p>

            {/* Bottom row: badges */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {/* Severity */}
              <span style={{
                fontSize: '9px', fontWeight: 800, textTransform: 'uppercase',
                letterSpacing: '0.08em', color, fontFamily: 'var(--font-mono)',
              }}>
                {inc.severity}
              </span>
              <span style={{ color: 'var(--text-3)', fontSize: '10px' }}>·</span>
              {/* Status */}
              <span style={{ fontSize: '10px', color: 'var(--text-3)' }}>
                {STATUS_LABEL[inc.status]}
              </span>
              <span style={{ color: 'var(--text-3)', fontSize: '10px' }}>·</span>
              {/* Source */}
              <span style={{ fontSize: '10px', color: 'var(--text-3)' }}>
                {inc.source_name}
              </span>
              {/* Area */}
              {inc.area_ha > 0 && (
                <>
                  <span style={{ color: 'var(--text-3)', fontSize: '10px', marginLeft: 'auto' }}>
                    {inc.area_ha} ha
                  </span>
                </>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
