// Mirrors `src/schema/pac_geg_schema.json`. Kept loose on purpose: the
// schema is still evolving and the UI only reads a subset of fields.

export type Family = 'PAC' | 'GEG'

export interface OperatingPoint {
  water_in_C?: number | null
  water_out_C?: number | null
  glycol_percent?: number | null
  air_temp_C?: number | null
  air_humidity_percent?: number | null
  load_percent?: number | null
}

export interface CoolingPerformance {
  power_kW?: number | null
  water_flow_lph?: number | null
  pressure_drop_kPa?: number | null
  eer?: number | null
  eer_uni?: number | null
  seer?: number | null
  total_power_kW?: number | null
  total_current_A?: number | null
}

export interface HeatingPerformance {
  power_kW?: number | null
  water_flow_lph?: number | null
  pressure_drop_kPa?: number | null
  cop?: number | null
  cop_uni?: number | null
  scop?: number | null
  eta_s_percent?: number | null
  seasonal_class?: string | null
  total_power_kW?: number | null
  total_current_A?: number | null
}

export interface Option {
  code: string
  category: string | null
  label: string
  description: string | null
  tips: string | null
  selected: boolean
  block?: number | null
  position?: number | null
  character?: string | null
  decoded?: boolean
}

export interface Warning {
  code: string
  message: string
  field: string | null
}

export interface CanonicalRecord {
  family: Family
  model: string
  size: string
  type: string
  designation_code: string | null
  designation_blocks: { block1: string | null; block2: string | null } | null
  conditions: { cooling?: OperatingPoint; heating?: OperatingPoint }
  performance: { cooling?: CoolingPerformance; heating?: HeatingPerformance }
  acoustic: Record<string, number | null>
  norm: Record<string, string | boolean | null>
  general: Record<string, string | number | null>
  options: Option[]
  warnings: Warning[]
  source: { filename: string; format: 'docx' | 'pdf'; extracted_at: string; parser_version: string }
}

export interface ParseResponse {
  data: CanonicalRecord
  warnings: Warning[]
}
