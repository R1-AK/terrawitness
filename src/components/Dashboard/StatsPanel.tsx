import type { Stats } from '../../lib/types'

interface Props { stats: Stats }

function Stat({ value, label, accent }: { value: string | number; label: string; accent?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <span style={{
        fontSize: '22px', fontWeight: 800, lineHeight: 1,
        letterSpacing: '-0.03em', color: accent ?? 'var(--text-1)',
        fontFamily: 'var(--font-mono)',
      }}>
        {value}
      </span>
      <span style={{ fontSize: '10px', color: 'var(--text-3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </span>
    </div>
  )
}

export default function StatsPanel({ stats }: Props) {
  const pct = Math.round((stats.verified / stats.total_incidents) * 100)
  return (
    <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        <Stat value={stats.total_incidents} label="Cases" />
        <Stat value={stats.violations_flagged} label="Violations" accent="var(--critical)" />
        <Stat value={stats.verified} label="Verified" accent="var(--ok)" />
        <Stat value={`${stats.area_cleared_ha.toLocaleString()} ha`} label="Area AOI" accent="var(--high)" />
      </div>
      <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ flex: 1, height: '2px', background: 'var(--border-2)', borderRadius: '1px', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: '1px',
            background: 'linear-gradient(to right, var(--ok), var(--accent))',
            width: `${pct}%`,
          }} />
        </div>
        <span style={{ fontSize: '10px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          {pct}% source-backed
        </span>
      </div>
    </div>
  )
}
