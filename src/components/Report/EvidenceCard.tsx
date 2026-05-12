import { ExternalLink, X } from 'lucide-react'
import type { Incident } from '../../lib/types'

const VIOLATION_FULL: Record<string, string> = {
  illegal_clearing:       'Illegal Forest Clearing',
  tailings_discharge:     'Tailings / Waste Discharge',
  unauthorized_expansion: 'Unauthorized Expansion',
  river_contamination:    'River Contamination',
  protected_area_breach:  'Protected Area Breach',
}

const SOURCE_LABEL: Record<Incident['source_type'], string> = {
  local_news:         'Local news',
  national_news:      'National news',
  investigation:      'Investigative reporting',
  official_statement: 'Official statement',
  public_social_post: 'Public social post',
  social_media:       'Social media post',
}

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--ok)',
}

interface Props {
  incident: Incident
  onClose: () => void
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
        {label}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-1)', lineHeight: 1.55 }}>
        {children}
      </div>
    </div>
  )
}

export default function EvidenceCard({ incident, onClose }: Props) {
  const sevColor = SEV_COLOR[incident.severity]
  const isPost = incident.source_type === 'public_social_post' || incident.source_type === 'social_media'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>

      {/* Header */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px',
        flexShrink: 0,
      }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: sevColor, flexShrink: 0, display: 'inline-block' }} />
            <span style={{ fontSize: '10px', fontWeight: 700, color: sevColor, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {incident.severity}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-3)' }}>{incident.id}</span>
          </div>
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.25, letterSpacing: '-0.01em' }}>
            {VIOLATION_FULL[incident.violation_type]}
          </h3>
        </div>
        <button
          onClick={onClose}
          style={{ flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: '2px', borderRadius: '4px', display: 'flex', alignItems: 'center' }}
        >
          <X size={14} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 8px' }}>

        {/* Quote */}
        <div style={{
          margin: '12px 0 4px',
          padding: '10px 12px',
          background: 'var(--surface-2)',
          borderLeft: `3px solid ${sevColor}`,
          borderRadius: '0 5px 5px 0',
        }}>
          <p style={{ fontSize: '12px', color: 'var(--text-2)', lineHeight: 1.6, fontStyle: 'italic' }}>
            "{incident.post_text}"
          </p>
        </div>

        <Row label="Location">
          {incident.location.desa}, {incident.location.kecamatan}
          <br />
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
            {incident.location.kabupaten} · {incident.location.provinsi}
          </span>
        </Row>

        <Row label="Observed zone">
          {incident.zone_name}
          <br />
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>{incident.zone_type}</span>
        </Row>

        {incident.concession_holder && (
          <Row label="Operator">
            <span style={{ color: 'var(--high)' }}>{incident.concession_holder}</span>
          </Row>
        )}

        {incident.lease_context && (
          <Row label="Mining lease">
            {incident.lease_context.name}
            <br />
            <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              {incident.lease_context.activity} · {incident.lease_context.commodity} · {incident.lease_context.area_ha.toLocaleString()} ha
            </span>
          </Row>
        )}

        {incident.location_proxy && (
          <Row label="Location proxy">
            <span style={{ color: 'var(--accent)' }}>{incident.location_proxy.method}</span>
            <br />
            <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              {incident.location_proxy.confidence} · ±{incident.location_proxy.uncertainty_km} km
            </span>
          </Row>
        )}

        <Row label="Source">
          <span style={{ fontWeight: 600 }}>{incident.source_name}</span>
          <span style={{ color: 'var(--text-3)', marginLeft: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            {incident.source_date}
          </span>
          <br />
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>{SOURCE_LABEL[incident.source_type]}</span>
        </Row>

        {incident.violation_flag && (
          <div style={{
            marginTop: '10px', marginBottom: '4px',
            padding: '7px 10px', borderRadius: '4px',
            background: 'rgba(196,28,28,0.05)', border: '1px solid rgba(196,28,28,0.15)',
            fontSize: '11px', color: 'var(--critical)',
          }}>
            Reported harm overlaps a sensitive ecological or livelihood-critical area.
          </div>
        )}
      </div>

      {/* Source link */}
      <div style={{ flexShrink: 0, padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
        <a href={incident.source_url} target="_blank" rel="noreferrer" className="source-link-button">
          {isPost ? 'Open post' : 'Open source article'}
          <ExternalLink size={11} />
        </a>
      </div>
    </div>
  )
}
