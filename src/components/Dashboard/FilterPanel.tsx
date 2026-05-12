import type { Incident } from '../../lib/types'

export interface Filters {
  year:     number | null
  month:    number | null
  provinsi: string | null
  severity: string | null
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

interface Props {
  incidents:      Incident[]
  filters:        Filters
  onFilterChange: (f: Partial<Filters>) => void
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div style={{
      fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em',
      textTransform: 'uppercase', color: 'var(--text-3)',
      marginBottom: '7px',
    }}>
      {label}
    </div>
  )
}

function Chip({
  label, active, color, disabled, onClick,
}: {
  label: string; active: boolean; color?: string; disabled?: boolean; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        fontSize: '12px', fontWeight: active ? 600 : 400,
        padding: '4px 10px', borderRadius: '5px',
        border: `1px solid ${active ? (color ?? 'var(--accent)') : 'var(--border)'}`,
        background: active ? (color ? `${color}18` : 'var(--accent-dim)') : 'transparent',
        color: active ? (color ?? 'var(--accent)') : disabled ? 'var(--border-2)' : 'var(--text-2)',
        cursor: disabled ? 'default' : 'pointer',
        transition: 'all 0.1s',
        lineHeight: 1.4,
      }}
    >
      {label}
    </button>
  )
}

export default function FilterPanel({ incidents, filters, onFilterChange }: Props) {
  const years = [...new Set(incidents.map(i => new Date(i.source_date).getFullYear()))].sort()

  const monthsWithData = new Set(
    filters.year
      ? incidents
          .filter(i => new Date(i.source_date).getFullYear() === filters.year)
          .map(i => new Date(i.source_date).getMonth())
      : []
  )

  const provinces = [...new Set(incidents.map(i => i.location.provinsi))].sort()

  // Provinces that have at least one case matching the other active filters
  const activeProvinces = new Set(
    incidents
      .filter(i => {
        const d = new Date(i.source_date)
        if (filters.year     && d.getFullYear() !== filters.year)   return false
        if (filters.month != null && d.getMonth() !== filters.month) return false
        if (filters.severity && i.severity !== filters.severity)     return false
        return true
      })
      .map(i => i.location.provinsi)
  )

  const severities: Array<'critical'|'high'|'medium'|'low'> = ['critical','high','medium','low']

  // Severities that have at least one case matching other active filters
  const activeSeverities = new Set(
    incidents
      .filter(i => {
        const d = new Date(i.source_date)
        if (filters.year     && d.getFullYear() !== filters.year)     return false
        if (filters.month != null && d.getMonth() !== filters.month)  return false
        if (filters.provinsi && i.location.provinsi !== filters.provinsi) return false
        return true
      })
      .map(i => i.severity)
  )

  const activeCount = Object.values(filters).filter(v => v !== null).length

  const toggle = <T,>(key: keyof Filters, val: T, current: T | null) =>
    onFilterChange({ [key]: current === val ? null : val, ...(key === 'year' ? { month: null } : {}) })

  return (
    <div style={{ padding: '12px 14px 14px', borderBottom: '1px solid var(--border)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-1)' }}>
          Filters{activeCount > 0 && (
            <span style={{
              marginLeft: '6px', fontSize: '11px', fontWeight: 700,
              background: 'var(--accent-dim)', color: 'var(--accent)',
              padding: '1px 6px', borderRadius: '8px',
            }}>{activeCount}</span>
          )}
        </span>
        {activeCount > 0 && (
          <button
            onClick={() => onFilterChange({ year: null, month: null, provinsi: null, severity: null })}
            style={{ fontSize: '11px', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Clear all ×
          </button>
        )}
      </div>

      {/* DATE */}
      <div style={{ marginBottom: '12px' }}>
        <SectionLabel label="Date" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {years.map(y => (
            <Chip
              key={y} label={String(y)}
              active={filters.year === y}
              onClick={() => toggle('year', y, filters.year)}
            />
          ))}
        </div>
        {filters.year && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '6px' }}>
            {MONTHS.map((m, idx) => (
              <Chip
                key={m} label={m}
                active={filters.month === idx}
                disabled={!monthsWithData.has(idx)}
                onClick={() => monthsWithData.has(idx) && toggle('month', idx, filters.month)}
              />
            ))}
          </div>
        )}
      </div>

      {/* LOCATION */}
      <div style={{ marginBottom: '12px' }}>
        <SectionLabel label="Location" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {provinces.map(p => (
            <Chip
              key={p} label={p}
              active={filters.provinsi === p}
              disabled={!activeProvinces.has(p)}
              onClick={() => activeProvinces.has(p) && toggle('provinsi', p, filters.provinsi)}
            />
          ))}
        </div>
      </div>

      {/* SEVERITY */}
      <div>
        <SectionLabel label="Severity" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {severities.filter(s => incidents.some(i => i.severity === s)).map(s => (
            <Chip
              key={s} label={s.charAt(0).toUpperCase() + s.slice(1)}
              active={filters.severity === s}
              disabled={!activeSeverities.has(s)}
              color={SEV_COLOR[s]}
              onClick={() => activeSeverities.has(s) && toggle('severity', s, filters.severity)}
            />
          ))}
        </div>
      </div>

    </div>
  )
}
