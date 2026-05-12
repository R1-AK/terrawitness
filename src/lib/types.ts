export type ViolationType =
  | 'illegal_clearing'
  | 'tailings_discharge'
  | 'unauthorized_expansion'
  | 'river_contamination'
  | 'protected_area_breach'

export type IncidentStatus = 'incoming' | 'geoparsing' | 'satellite' | 'landuse' | 'verified' | 'routed'
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low'
export type SourceType =
  | 'local_news'
  | 'national_news'
  | 'investigation'
  | 'official_statement'
  | 'public_social_post'
  | 'social_media'

export interface Incident {
  id: string
  status: IncidentStatus
  severity: SeverityLevel
  location: {
    lat: number
    lng: number
    desa: string
    kecamatan: string
    kabupaten: string
    provinsi: string
  }
  violation_type: ViolationType
  zone_name: string
  zone_type: string
  violation_flag: boolean
  change_score: number        // 0–1
  ndvi_before: number
  ndvi_after: number
  area_ha: number
  post_text: string
  post_date: string
  report_date: string
  source_type: SourceType
  source_name: string
  source_url: string
  source_date: string
  concession_holder?: string
  lease_context?: {
    name: string
    license_type: string
    activity: string
    commodity: string
    area_ha: number
    polygon: { lat: number; lng: number }[]
  }
  location_proxy?: {
    method: string
    confidence: string
    uncertainty_km: number
    evidence: string[]
  }
  lease_match?: {
    name: string
    activity: string
    commodity: string
    area_ha: number
    dist_km: number
    centroid: [number, number]
  }
  signal_type?: string
  witness_score?: number
  thumbnail_before?: string
  thumbnail_after?: string
}

export interface Stats {
  total_incidents: number
  verified: number
  violations_flagged: number
  area_cleared_ha: number
  provinces_active: number
}
