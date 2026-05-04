import type { CanonicalRecord } from '../api/types'

export const pacRecord: CanonicalRecord = {
  family: 'PAC',
  model: 'PLP',
  size: '052',
  type: 'HS',
  designation_code: 'PLP052HS2B A000CE000I00110 0000000I000000000000',
  designation_blocks: { block1: 'A000CE000I00110', block2: '0000000I000000000000' },
  conditions: {
    cooling: { water_in_C: 12.0, water_out_C: 7.0, air_temp_C: 35.0, load_percent: 100 },
    heating: { water_in_C: 40.0, water_out_C: 45.0, air_temp_C: 7.0, air_humidity_percent: 87 },
  },
  performance: {
    cooling: { power_kW: 41.7, water_flow_lph: 7155, eer: 2.5, seer: 4.15 },
    heating: { power_kW: 52.3, water_flow_lph: 9087, cop: 3.37, scop: 4.35, seasonal_class: 'A++' },
  },
  acoustic: { free_field_distance_m: 10.0, directionality_factor: 2.0 },
  norm: { uni_en_14511_applied: true, uni_en_14511_version: 'UNI EN 14511 - 2022' },
  general: {
    max_current_A: 56,
    sound_power_lw_dBA: 83,
    refrigerant: 'R290',
    gwp: 3,
    weight_kg: 500,
    supply: '400 / 3+N / 50',
  },
  options: [
    {
      code: 'B1P00',
      category: 'designation',
      label: "Option codee position B1P00 = 'A' (a renseigner)",
      description: null,
      tips: null,
      selected: true,
      block: 1,
      position: 0,
      character: 'A',
      decoded: false,
    },
  ],
  warnings: [],
  source: {
    filename: 'sample.docx',
    format: 'docx',
    extracted_at: '2026-04-28T07:00:00Z',
    parser_version: '0.3.0',
  },
}
