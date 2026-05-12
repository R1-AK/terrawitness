import type { Stats } from '../../lib/types'

interface Props { stats: Stats }

export default function StatsPanel({ stats }: Props) {
  return (
    <div style={{
      padding: '14px 16px 12px',
      borderBottom: '1px solid var(--border)',
      display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0',
    }}>
      {[
        { value: stats.total_incidents,    label: 'Cases',      color: 'var(--text-1)' },
        { value: stats.violations_flagged, label: 'Violations', color: 'var(--critical)' },
        { value: stats.verified,           label: 'Verified',   color: 'var(--ok)' },
      ].map(({ value, label, color }, i) => (
        <div key={label} style={{
          display: 'flex', flexDirection: 'column', gap: '3px',
          padding: '0 12px 0 0',
          borderRight: i < 2 ? '1px solid var(--border)' : 'none',
          marginRight: i < 2 ? '12px' : '0',
        }}>
          <span style={{
            fontSize: '20px', fontWeight: 800, lineHeight: 1,
            letterSpacing: '-0.03em', color,
            fontFamily: 'var(--font-mono)',
          }}>
            {value}
          </span>
          <span style={{
            fontSize: '10px', color: 'var(--text-3)', fontWeight: 500,
            textTransform: 'uppercase', letterSpacing: '0.08em',
          }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  )
}
