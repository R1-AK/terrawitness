import type { Incident } from '../../lib/types'

interface Props {
  incidents: Incident[]
  selectedYear: number | null
  onYearSelect: (year: number | null) => void
}

export default function TimelineFilter({ incidents, selectedYear, onYearSelect }: Props) {
  const yearCounts: Record<number, number> = {}
  for (const inc of incidents) {
    const y = new Date(inc.source_date).getFullYear()
    yearCounts[y] = (yearCounts[y] ?? 0) + 1
  }

  const years = Object.keys(yearCounts).map(Number).sort()
  const maxCount = Math.max(...Object.values(yearCounts))
  const peakYear = years.find(y => yearCounts[y] === maxCount)!

  return (
    <div style={{ padding: '10px 16px 12px', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
          Timeline
        </span>
        {selectedYear && (
          <button
            onClick={() => onYearSelect(null)}
            style={{ fontSize: '10px', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-ui)' }}
          >
            Clear ×
          </button>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '36px', marginBottom: '6px' }}>
        {/* All bar */}
        <button
          onClick={() => onYearSelect(null)}
          title="All years"
          style={{
            width: '28px', height: '100%', borderRadius: '3px 3px 0 0', border: 'none', cursor: 'pointer',
            background: !selectedYear ? 'var(--accent)' : 'var(--border-2)',
            transition: 'background 0.15s',
            flexShrink: 0,
          }}
        />

        {/* Year bars */}
        {years.map(year => {
          const count = yearCounts[year]
          const barH = Math.max(6, Math.round((count / maxCount) * 36))
          const isPeak = year === peakYear
          const isSelected = selectedYear === year
          const barColor = isSelected
            ? 'var(--accent)'
            : isPeak
              ? 'var(--critical)'
              : 'var(--border-2)'

          return (
            <button
              key={year}
              onClick={() => onYearSelect(isSelected ? null : year)}
              title={`${year}: ${count} incident${count !== 1 ? 's' : ''}`}
              style={{
                flex: 1, height: `${barH}px`, borderRadius: '3px 3px 0 0',
                border: 'none', cursor: 'pointer',
                background: barColor,
                transition: 'background 0.15s, height 0.2s',
                alignSelf: 'flex-end',
              }}
            />
          )
        })}
      </div>

      {/* Year labels */}
      <div style={{ display: 'flex', gap: '4px' }}>
        <div style={{ width: '28px', flexShrink: 0, textAlign: 'center', fontSize: '9px', color: !selectedYear ? 'var(--accent)' : 'var(--text-3)', fontFamily: 'var(--font-mono)', fontWeight: !selectedYear ? 700 : 400 }}>
          ALL
        </div>
        {years.map(year => {
          const isPeak = year === peakYear
          const isSelected = selectedYear === year
          return (
            <div key={year} style={{
              flex: 1, textAlign: 'center',
              fontSize: '9px', fontFamily: 'var(--font-mono)',
              color: isSelected ? 'var(--accent)' : isPeak ? 'var(--critical)' : 'var(--text-3)',
              fontWeight: isSelected || isPeak ? 700 : 400,
            }}>
              {String(year).slice(2)}
            </div>
          )
        })}
      </div>
    </div>
  )
}
