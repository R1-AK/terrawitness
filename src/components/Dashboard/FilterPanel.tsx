import type { Incident } from '../../lib/types'

export interface Filters {
  year:      number | null
  month:     number | null
  provinsi:  string | null
  violation: string | null
  severity:  string | null
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

const VIOLATION_SHORT: Record<string, string> = {
  illegal_clearing:       'Clearing',
  tailings_discharge:     'Tailings',
  unauthorized_expansion: 'Expansion',
  river_contamination:    'River',
  protected_area_breach:  'Protected area',
}

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

interface Props {
  incidents:       Incident[]
  filters:         Filters
  onFilterChange:  (f: Partial<Filters>) => void
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div style={{
      fontSize: '9px', fontWeight: 700, letterSpacing: '0.12em',
      textTransform: 'uppercase', color: 'var(--text-3)',
      marginBottom: '6px',
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
        fontSize: '11px', fontWeight: active ? 600 : 400,
        padding: '3px 8px', borderRadius: '4px',
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
  // Derive available values from data
  const years = [...new Set(incidents.map(i => new Date(i.source_date).getFullYear()))].sort()

  const monthsWithData = new Set(
    filters.year
      ? incidents
          .filter(i => new Date(i.source_date).getFullYear() === filters.year)
          .map(i => new Date(i.source_date).getMonth())
      : []
  )

  const provinces = [...new Set(incidents.map(i => i.location.provinsi))].sort()
  const violations = [...new Set(incidents.map(i => i.violation_type))]
  const severities: Array<'critical'|'high'|'medium'|'low'> = ['critical','high','medium','low']

  const activeCount = [filters.year, filters.month, filters.provinsi, filters.violation, filters.severity]
    .filter(Boolean).length

  const toggle = <T,>(key: keyof Filters, val: T, current: T | null) =>
    onFilterChange({ [key]: current === val ? null : val, ...(key === 'year' ? { month: null } : {}) })

  return (
    <div style={{ padding: '10px 14px 12px', borderBottom: '1px solid var(--border)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-2)' }}>
          Filters {activeCount > 0 && (
            <span style={{
              marginLeft: '4px', fontSize: '10px', fontWeight: 700,
              background: 'var(--accent-dim)', color: 'var(--accent)',
              padding: '1px 5px', borderRadius: '8px',
            }}>{activeCount}</span>
          )}
        </span>
        {activeCount > 0 && (
          <button
            onClick={() => onFilterChange({ year: null, month: null, provinsi: null, violation: null, severity: null })}
            style={{ fontSize: '10px', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Clear all ×
          </button>
        )}
      </div>

      {/* DATE */}
      <div style={{ marginBottom: '10px' }}>
        <SectionLabel label="Date" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {years.map(y => (
            <Chip
              key={y} label={String(y)}
              active={filters.year === y}
              onClick={() => toggle('year', y, filters.year)}
            />
          ))}
        </div>

        {/* Month row — shown when a year is selected */}
        {filters.year && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '5px' }}>
            {MONTHS.map((m, idx) => (
              <Chip
                key={m} label={m}
                active={filters.month === idx}
                disabled={!monthsWithData.has(idx)}
                onClick={() => !monthsWithData.has(idx) ? undefined : toggle('month', idx, filters.month)}
              />
            ))}
          </div>
        )}
      </div>

      {/* LOCATION */}
      <div style={{ marginBottom: '10px' }}>
        <SectionLabel label="Location" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {provinces.map(p => (
            <Chip
              key={p} label={p}
              active={filters.provinsi === p}
              onClick={() => toggle('provinsi', p, filters.provinsi)}
            />
          ))}
        </div>
      </div>

      {/* VIOLATION TYPE */}
      <div style={{ marginBottom: '10px' }}>
        <SectionLabel label="Violation type" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {violations.map(v => (
            <Chip
              key={v} label={VIOLATION_SHORT[v] ?? v}
              active={filters.violation === v}
              onClick={() => toggle('violation', v, filters.violation)}
            />
          ))}
        </div>
      </div>

      {/* SEVERITY */}
      <div>
        <SectionLabel label="Severity" />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {severities.filter(s => incidents.some(i => i.severity === s)).map(s => (
            <Chip
              key={s} label={s.charAt(0).toUpperCase() + s.slice(1)}
              active={filters.severity === s}
              color={SEV_COLOR[s]}
              onClick={() => toggle('severity', s, filters.severity)}
            />
          ))}
        </div>
      </div>

    </div>
  )
}
