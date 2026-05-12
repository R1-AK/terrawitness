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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
        {label}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-1)', lineHeight: 1.6 }}>
        {children}
      </div>
    </div>
  )
}

export default function EvidenceCard({ incident, onClose }: Props) {
  const sevColor = SEV_COLOR[incident.severity]
  const sourceLinkLabel = incident.source_type === 'public_social_post' ? 'Open post' : 'Open source article'

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{
              fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em',
              color: sevColor, fontFamily: 'var(--font-mono)',
            }}>
              {incident.severity}
            </span>
            <span style={{ fontSize: '9px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
              {incident.id}
            </span>
          </div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.25, letterSpacing: '-0.01em' }}>
            {VIOLATION_FULL[incident.violation_type]}
          </h3>
        </div>
        <button
          onClick={onClose}
          style={{
            flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-3)', padding: '2px', borderRadius: '4px',
            display: 'flex', alignItems: 'center',
          }}
        >
          <X size={15} />
        </button>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 8px' }}>

        {/* Core signal quote */}
        <div style={{
          margin: '12px 0',
          padding: '12px',
          background: 'var(--surface-2)',
          border: '1px solid var(--border-2)',
          borderLeft: `3px solid ${sevColor}`,
          borderRadius: '0 6px 6px 0',
        }}>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px', fontFamily: 'var(--font-mono)' }}>
            Core signal
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-1)', lineHeight: 1.65, fontStyle: 'italic' }}>
            "{incident.post_text}"
          </p>
        </div>

        {/* Fields */}
        <Field label="Location">
          <span style={{ color: 'var(--text-1)' }}>
            {incident.location.desa}, {incident.location.kecamatan}
          </span>
          <br />
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
            {incident.location.kabupaten} · {incident.location.provinsi}
          </span>
        </Field>

        <Field label="Observed zone">
          <span>{incident.zone_name}</span>
          <br />
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>{incident.zone_type}</span>
        </Field>

        {incident.concession_holder && (
          <Field label="Associated operator">
            <span style={{ color: 'var(--high)' }}>{incident.concession_holder}</span>
          </Field>
        )}

        {incident.location_proxy && (
          <Field label="Location proxy">
            <span style={{ color: 'var(--accent)', fontSize: '11px' }}>{incident.location_proxy.method}</span>
            <br />
            <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              {incident.location_proxy.confidence} · ±{incident.location_proxy.uncertainty_km} km
            </span>
          </Field>
        )}

        {incident.lease_context && (
          <Field label="Mining lease match">
            <span>{incident.lease_context.name}</span>
            <br />
            <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              {incident.lease_context.activity} · {incident.lease_context.commodity} · {incident.lease_context.area_ha.toLocaleString()} ha
            </span>
            <br />
            <span style={{ fontSize: '11px', color: 'var(--text-3)' }}>
              Permit: {incident.lease_context.license_type} · WIUP_2025 polygon
            </span>
          </Field>
        )}

        <Field label="Documented source">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600 }}>{incident.source_name}</span>
            <span style={{ fontSize: '10px', color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>{incident.source_date}</span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-2)' }}>{SOURCE_LABEL[incident.source_type]}</span>
        </Field>

        {incident.violation_flag && (
          <div style={{
            marginTop: '10px', padding: '8px 12px',
            background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.18)',
            borderRadius: '5px', fontSize: '11px', color: 'rgba(244,63,94,0.8)',
            fontWeight: 600,
          }}>
            Reported harm overlaps a sensitive ecological or livelihood-critical area.
          </div>
        )}
      </div>

      {/* Pinned source link */}
      <div style={{ flexShrink: 0, padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
        <a
          href={incident.source_url}
          target="_blank"
          rel="noreferrer"
          className="source-link-button"
        >
          {sourceLinkLabel}
          <ExternalLink size={11} />
        </a>
      </div>
    </div>
  )
}
