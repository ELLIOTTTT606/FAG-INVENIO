/**
 * Convert a French postal code into the most likely department code.
 *
 * Rules:
 *  - Code postal de 5 chiffres requis ; sinon retourne null.
 *  - 200xx -> 2A (Corse-du-Sud), 201xx -> 2B (Haute-Corse), 202xx-209xx -> 2B
 *    (les codes postaux corses pivotent autour de 20100 ; on suit la convention
 *    INSEE en mappant >= 20200 sur 2B).
 *  - 97xxx -> 971/972/973/974/976 (DROM) ; 98xxx -> 986/987/988 (COM).
 *  - Sinon -> les deux premiers chiffres.
 */
export function departmentFromPostalCode(postal: string): string | null {
  const trimmed = postal.trim()
  if (!/^\d{5}$/.test(trimmed)) return null

  if (trimmed.startsWith('20')) {
    const num = Number(trimmed)
    return num < 20200 ? '2A' : '2B'
  }
  if (trimmed.startsWith('97') || trimmed.startsWith('98')) {
    return trimmed.slice(0, 3)
  }
  return trimmed.slice(0, 2)
}
