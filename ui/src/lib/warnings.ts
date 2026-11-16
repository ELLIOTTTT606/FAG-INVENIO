import type { Warning } from '../api/types'

/** French wording of the parsers' warning codes (src/parser). */
const LABELS: Record<string, string> = {
  designation_decoder_missing:
    'Désignation non décodée : les options retenues doivent être cochées à la main.',
  designation_not_found: 'Code de désignation introuvable dans la fiche importée.',
  family_mismatch: 'La famille détectée ne correspond pas au modèle.',
  coercion_failed: 'Une valeur n’a pas pu être lue comme un nombre.',
  unit_mismatch: 'Une unité inattendue a été rencontrée.',
  pdf_no_text: 'Le PDF ne contient pas de texte exploitable (scan ?).',
}

export function warningLabel(warning: Warning): string {
  return LABELS[warning.code] ?? warning.message
}
