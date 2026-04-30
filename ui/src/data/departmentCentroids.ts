// Approximate centroids (lat, lon) for every French departement.
// Sourced from the public administrative geography (INSEE / Wikipedia) and
// rounded to two decimals; precision is intentionally low because the map
// projects them to a coarse SVG grid. dx/dy are pixel nudges used to
// disambiguate overlapping centroids in the Ile-de-France cluster.

export interface Centroid {
  code: string
  lat: number
  lon: number
  /** Optional pixel offset applied AFTER projection (used for IDF overlap). */
  dx?: number
  dy?: number
}

export const METROPOLE_CENTROIDS: Centroid[] = [
  { code: '01', lat: 46.10, lon: 5.35 },
  { code: '02', lat: 49.55, lon: 3.62 },
  { code: '03', lat: 46.40, lon: 3.20 },
  { code: '04', lat: 44.10, lon: 6.30 },
  { code: '05', lat: 44.65, lon: 6.30 },
  { code: '06', lat: 43.92, lon: 7.20 },
  { code: '07', lat: 44.75, lon: 4.40 },
  { code: '08', lat: 49.65, lon: 4.65 },
  { code: '09', lat: 42.95, lon: 1.55 },
  { code: '10', lat: 48.30, lon: 4.20 },
  { code: '11', lat: 43.10, lon: 2.55 },
  { code: '12', lat: 44.30, lon: 2.65 },
  { code: '13', lat: 43.55, lon: 5.05 },
  { code: '14', lat: 49.10, lon: -0.40 },
  { code: '15', lat: 45.05, lon: 2.65 },
  { code: '16', lat: 45.65, lon: 0.20 },
  { code: '17', lat: 45.85, lon: -0.85 },
  { code: '18', lat: 46.95, lon: 2.40 },
  { code: '19', lat: 45.30, lon: 1.85 },
  { code: '21', lat: 47.50, lon: 4.65 },
  { code: '22', lat: 48.45, lon: -2.95 },
  { code: '23', lat: 46.05, lon: 2.05 },
  { code: '24', lat: 45.10, lon: 0.75 },
  { code: '25', lat: 47.10, lon: 6.35 },
  { code: '26', lat: 44.65, lon: 5.10 },
  { code: '27', lat: 49.05, lon: 1.20 },
  { code: '28', lat: 48.40, lon: 1.30 },
  { code: '29', lat: 48.30, lon: -4.10 },
  { code: '30', lat: 44.05, lon: 4.20 },
  { code: '31', lat: 43.40, lon: 1.40 },
  { code: '32', lat: 43.65, lon: 0.40 },
  { code: '33', lat: 44.85, lon: -0.55 },
  { code: '34', lat: 43.65, lon: 3.50 },
  { code: '35', lat: 48.10, lon: -1.70 },
  { code: '36', lat: 46.70, lon: 1.55 },
  { code: '37', lat: 47.20, lon: 0.70 },
  { code: '38', lat: 45.10, lon: 5.55 },
  { code: '39', lat: 46.65, lon: 5.70 },
  { code: '40', lat: 43.95, lon: -0.85 },
  { code: '41', lat: 47.55, lon: 1.40 },
  { code: '42', lat: 45.65, lon: 4.30 },
  { code: '43', lat: 45.10, lon: 3.85 },
  { code: '44', lat: 47.30, lon: -1.65 },
  { code: '45', lat: 47.95, lon: 2.30 },
  { code: '46', lat: 44.55, lon: 1.55 },
  { code: '47', lat: 44.30, lon: 0.55 },
  { code: '48', lat: 44.55, lon: 3.50 },
  { code: '49', lat: 47.40, lon: -0.55 },
  { code: '50', lat: 49.10, lon: -1.20 },
  { code: '51', lat: 48.95, lon: 4.40 },
  { code: '52', lat: 48.10, lon: 5.10 },
  { code: '53', lat: 48.10, lon: -0.65 },
  { code: '54', lat: 48.95, lon: 6.10 },
  { code: '55', lat: 49.00, lon: 5.40 },
  { code: '56', lat: 47.85, lon: -2.90 },
  { code: '57', lat: 49.05, lon: 6.65 },
  { code: '58', lat: 47.10, lon: 3.60 },
  { code: '59', lat: 50.60, lon: 3.10 },
  { code: '60', lat: 49.40, lon: 2.40 },
  { code: '61', lat: 48.65, lon: 0.10 },
  { code: '62', lat: 50.50, lon: 2.40 },
  { code: '63', lat: 45.75, lon: 3.10 },
  { code: '64', lat: 43.30, lon: -0.80 },
  { code: '65', lat: 43.05, lon: 0.15 },
  { code: '66', lat: 42.65, lon: 2.45 },
  { code: '67', lat: 48.65, lon: 7.65 },
  { code: '68', lat: 47.85, lon: 7.30 },
  { code: '69', lat: 45.85, lon: 4.65 },
  { code: '70', lat: 47.65, lon: 6.10 },
  { code: '71', lat: 46.65, lon: 4.55 },
  { code: '72', lat: 47.95, lon: 0.20 },
  { code: '73', lat: 45.50, lon: 6.40 },
  { code: '74', lat: 46.05, lon: 6.45 },
  { code: '75', lat: 48.85, lon: 2.35 },
  { code: '76', lat: 49.65, lon: 1.10 },
  { code: '77', lat: 48.50, lon: 2.85 },
  { code: '78', lat: 48.85, lon: 1.80 },
  { code: '79', lat: 46.50, lon: -0.30 },
  { code: '80', lat: 49.95, lon: 2.30 },
  { code: '81', lat: 43.80, lon: 2.10 },
  { code: '82', lat: 44.10, lon: 1.20 },
  { code: '83', lat: 43.50, lon: 6.30 },
  { code: '84', lat: 44.00, lon: 5.20 },
  { code: '85', lat: 46.70, lon: -1.30 },
  { code: '86', lat: 46.60, lon: 0.55 },
  { code: '87', lat: 45.85, lon: 1.30 },
  { code: '88', lat: 48.20, lon: 6.30 },
  { code: '89', lat: 47.80, lon: 3.55 },
  { code: '90', lat: 47.65, lon: 6.85 },
  // IDF cluster: 75/92/93/94 share the same centroid; nudge to disambiguate.
  { code: '91', lat: 48.55, lon: 2.30 },
  { code: '92', lat: 48.85, lon: 2.20, dx: -14 },
  { code: '93', lat: 48.95, lon: 2.45, dx: 12, dy: -6 },
  { code: '94', lat: 48.80, lon: 2.50, dx: 12, dy: 8 },
  { code: '95', lat: 49.10, lon: 2.20 },
  // Corse
  { code: '2A', lat: 41.85, lon: 8.95 },
  { code: '2B', lat: 42.45, lon: 9.15 },
]

/** DROM inset coordinates (already in SVG pixels, rendered as a separate panel). */
export interface DromEntry {
  code: string
  cx: number
  cy: number
}

export const DROM_LAYOUT: DromEntry[] = [
  { code: '971', cx: 30, cy: 20 },
  { code: '972', cx: 80, cy: 20 },
  { code: '973', cx: 30, cy: 60 },
  { code: '974', cx: 80, cy: 60 },
  { code: '976', cx: 130, cy: 60 },
]
