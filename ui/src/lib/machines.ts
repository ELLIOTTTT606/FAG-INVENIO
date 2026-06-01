// ─────────────────────────────────────────────────────────────────────────────
// Catalogue complet des machines GALLETTI
// Source : invenio-preview.jsx + CONSIGNE_INVENIO
// ─────────────────────────────────────────────────────────────────────────────

export type MachineFamily = 'PAC' | 'GEG' | 'PAC_GEG'
export type MediumType    = 'air_eau' | 'eau_eau'
export type Fluid         = 'R290' | 'R32' | 'R454B' | 'R410A'
export type AcousticType  = 'S' | 'L'   // Standard / Low-noise

export interface MachineModel {
  code:   string
  family: MachineFamily
  fluid:  Fluid
  medium: MediumType
  sizes:  string[]
}

// ── Catalogue ─────────────────────────────────────────────────────────────────
export const MACHINES: MachineModel[] = [
  // ── R290 ──────────────────────────────────────────────────────────────────
  {
    code: 'PLP', family: 'PAC', fluid: 'R290', medium: 'air_eau',
    sizes: ['37', '45', '52', '57', '62'],
  },
  {
    code: 'PLN', family: 'PAC', fluid: 'R290', medium: 'air_eau',
    sizes: ['52', '72', '82', '104', '114', '134', '154'],
  },
  // ── R32 ───────────────────────────────────────────────────────────────────
  {
    code: 'MLI', family: 'PAC_GEG', fluid: 'R32', medium: 'air_eau',
    sizes: ['06', '08', '10', '12', '16', '18', '26', '30'],
  },
  // ── R454B ─────────────────────────────────────────────────────────────────
  {
    code: 'PLE', family: 'PAC_GEG', fluid: 'R454B', medium: 'air_eau',
    sizes: ['52', '62', '72', '82', '92', '102', '122', '132', '142', '152'],
  },
  {
    code: 'PLI', family: 'PAC', fluid: 'R454B', medium: 'air_eau',
    sizes: ['35', '40', '45', '50'],
  },
  {
    code: 'GLE', family: 'GEG', fluid: 'R454B', medium: 'air_eau',
    sizes: ['658', '748', '818', '900', '942', '1072'],
  },
  {
    code: 'VLS', family: 'PAC_GEG', fluid: 'R454B', medium: 'air_eau',
    sizes: ['162', '202', '234', '254', '274', '314', '344', '374', '414', '456', '576'],
  },
  // ── R410A ─────────────────────────────────────────────────────────────────
  {
    code: 'VRS', family: 'PAC_GEG', fluid: 'R410A', medium: 'air_eau',
    sizes: ['162', '202', '234', '254', '274', '314', '344', '374', '414', '456', '546', '576'],
  },
  {
    code: 'MPE', family: 'GEG', fluid: 'R410A', medium: 'air_eau',
    sizes: ['04','05','08','09','10','13','14','15','18','21','24','27','28','30','35','40','42','54','61','66','69','76'],
  },
  {
    code: 'MPED', family: 'GEG', fluid: 'R410A', medium: 'air_eau',
    sizes: ['07','08','10','13','15','18','20','24','27','28','30','32','34','35','40','45','54','61','66','69','76'],
  },
  {
    code: 'LCC', family: 'PAC_GEG', fluid: 'R410A', medium: 'eau_eau',
    sizes: ['52','62','72','82','92','102','112','132','142','162','182','204'],
  },
  {
    code: 'LCX', family: 'PAC_GEG', fluid: 'R410A', medium: 'eau_eau',
    sizes: ['92','102','122','124','142','144','162','164','174','194','214','244','274','294','324','364'],
  },
  {
    code: 'EVITECH', family: 'GEG', fluid: 'R410A', medium: 'air_eau',
    sizes: ['52','62','72','82','92','104','124','154','174','184'],
  },
]

// ── Helpers ───────────────────────────────────────────────────────────────────
export const FLUIDS: { code: Fluid; models: string[] }[] = [
  { code: 'R290',  models: ['PLP', 'PLN'] },
  { code: 'R32',   models: ['MLI'] },
  { code: 'R454B', models: ['PLE', 'PLI', 'GLE', 'VLS'] },
  { code: 'R410A', models: ['VRS', 'MPE', 'MPED', 'LCC', 'LCX', 'EVITECH'] },
]

export function findMachine(code: string): MachineModel | undefined {
  return MACHINES.find(m => m.code === code)
}

export function getMediumLabel(medium: MediumType): string {
  return medium === 'air_eau' ? 'air/eau' : 'eau/eau'
}

export function getFamilyLabel(family: MachineFamily, medium: MediumType): string {
  const med = getMediumLabel(medium)
  return family === 'GEG'
    ? `Fiche de sélection d'un groupe d'eau glacée ${med}`
    : `Fiche de sélection d'une pompe à chaleur ${med}`
}

// Détection automatique depuis le nom de fichier GALLETTI (ex: PLP052HS.docx)
export function parseFilename(filename: string): {
  model:    string | null
  size:     string | null
  family:   'PAC' | 'GEG' | null
  acoustic: AcousticType | null
} {
  const upper = filename.replace(/\.[^.]+$/, '').toUpperCase()

  // Tri par longueur de code décroissante pour éviter les faux positifs (MPED avant MPE)
  const sorted = [...MACHINES].sort((a, b) => b.code.length - a.code.length)

  for (const m of sorted) {
    if (!upper.startsWith(m.code)) continue
    const rest   = upper.slice(m.code.length)
    const sizeM  = rest.match(/^(\d+)/)
    if (!sizeM) return { model: m.code, size: null, family: null, acoustic: null }

    const size      = sizeM[1]
    const afterSize = rest.slice(size.length)

    const family:   'PAC' | 'GEG' | null = /H/.test(afterSize) ? 'PAC' : /C/.test(afterSize) ? 'GEG' : null
    const acoustic: AcousticType | null   = /L/.test(afterSize) ? 'L' : /S/.test(afterSize) ? 'S' : null

    // Normalise la taille pour correspondre au catalogue (retire les zéros en tête)
    const normalised = m.sizes.find(s => s === size) ?? size

    return { model: m.code, size: normalised, family, acoustic }
  }

  return { model: null, size: null, family: null, acoustic: null }
}
