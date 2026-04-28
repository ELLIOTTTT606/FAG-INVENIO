"""Synthetic PDF fixtures matching the GALLETTI structure.

Built with reportlab so that pdfplumber's lattice-based table extractor
can recover the (label, unit, value) triples without OCR. The content
mirrors `galletti_docx.py` so that the two parsers can be compared.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _styled_table(rows: list[tuple[str, str, str]]) -> Table:
    table = Table(rows, colWidths=[90 * mm, 25 * mm, 35 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _build_story(
    *,
    designation: str,
    cooling_conditions: list[tuple[str, str, str]],
    heating_conditions: list[tuple[str, str, str]] | None,
    cooling_perf: list[tuple[str, str, str]],
    heating_perf: list[tuple[str, str, str]] | None,
    general: list[tuple[str, str, str]],
) -> list[object]:
    styles = getSampleStyleSheet()
    title_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story: list[object] = []
    story.append(Paragraph("PROPOSITION DE PROJET", styles["Title"]))
    story.append(Paragraph(f"Reference : {designation}", body_style))
    story.append(
        Paragraph(
            "Agence : FRANCE AIR - 383 rue des Barronnieres - 01700 Beynost - "
            "Donnees : 13-02-2026",
            body_style,
        )
    )
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Refroidissement", title_style))
    story.append(_styled_table(cooling_conditions))
    story.append(Spacer(1, 4 * mm))

    if heating_conditions:
        story.append(Paragraph("Chauffage", title_style))
        story.append(_styled_table(heating_conditions))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Donnees acoustiques", title_style))
    story.append(
        _styled_table(
            [
                ("Distance en champ libre", "m", "10.0"),
                ("Facteur de directionnalite", "", "2"),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Norme UNI EN 14511", title_style))
    story.append(
        _styled_table(
            [
                ("Calculs selon la norme UNI EN 14511", "", "Oui"),
                ("UNI EN 14511 Version", "", "UNI EN 14511 - 2022"),
            ]
        )
    )

    story.append(PageBreak())

    story.append(Paragraph("Refroidissement (Performances)", title_style))
    story.append(_styled_table(cooling_perf))
    story.append(Spacer(1, 4 * mm))

    if heating_perf:
        story.append(Paragraph("Chauffage (Performances)", title_style))
        story.append(_styled_table(heating_perf))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Donnees generales", title_style))
    story.append(_styled_table(general))

    return story


def write_pac(path: Path) -> Path:
    cooling_conditions = [
        ("Temp. entree eau utilisation", "C", "12.0"),
        ("Temp. sortie eau utilisation", "C", "7.0"),
        ("Glycol cote utilisation", "%", "0"),
        ("Temp. air exterieur source", "C", "35.0"),
        ("Humidite relative air source", "%", "40"),
        ("Pourcentage de charge", "%", "100"),
    ]
    heating_conditions = [
        ("Temp. entree eau utilisation", "C", "40.0"),
        ("Temp. sortie eau utilisation", "C", "45.0"),
        ("Glycol cote utilisation", "%", "0"),
        ("Temp. air exterieur source", "C", "7.0"),
        ("Humidite relative air source", "%", "87"),
        ("Pourcentage de charge", "%", "100"),
    ]
    cooling_perf = [
        ("Puissance frigorifique", "kW", "41.7"),
        ("Debit eau utilisateur", "l/h", "7155"),
        ("Perte de charge utilisateur", "kPa", "30"),
        ("Puissance absorbee compresseurs", "kW", "16.0"),
        ("Courant absorbe compresseurs", "A", "25.6"),
        ("Puissance absorbee totale", "kW", "16.6"),
        ("Courant absorbe total", "A", "28.8"),
        ("EER", "W/W", "2.50"),
        ("EER UNI EN 14511", "W/W", "2.48"),
        ("SEER", "Wh/Wh", "4.15"),
    ]
    heating_perf = [
        ("Puissance calorifique", "kW", "52.3"),
        ("Debit eau utilisateur", "l/h", "9087"),
        ("Perte de charge utilisateur", "kPa", "48"),
        ("Puissance absorbee compresseurs", "kW", "14.8"),
        ("Courant absorbe compresseurs", "A", "23.8"),
        ("Puissance absorbee totale", "kW", "15.5"),
        ("Courant absorbe total", "A", "27.0"),
        ("COP", "W/W", "3.37"),
        ("COP UNI EN 14511", "W/W", "3.32"),
        ("SCOP", "Wh/Wh", "4.35"),
        ("Eta s", "", "171.0"),
        ("Classe saisonniere chauffage", "", "A++"),
    ]
    general = [
        ("Max courant absorbe (FLA)", "A", "56"),
        ("Courant de demarrage (LRA)", "A", "57"),
        ("Niveau de puissance acoustique Lw", "dB(A)", "83"),
        ("Niveau de pression acoustique Lp", "dB(A)", "55"),
        ("Debit d'air source", "m3/h", "16259"),
        ("Nombre de ventilateurs", "", "2"),
        ("Refrigerant", "", "R290"),
        ("GWP", "", "3"),
        ("Poids sans options", "kg", "500"),
        ("Alimentation", "", "400 / 3+N / 50"),
    ]

    story = _build_story(
        designation="PLP052HS2B A000CE000I00110 0000000I000000000000",
        cooling_conditions=cooling_conditions,
        heating_conditions=heating_conditions,
        cooling_perf=cooling_perf,
        heating_perf=heating_perf,
        general=general,
    )
    SimpleDocTemplate(str(path), pagesize=A4).build(story)
    return path


def write_geg(path: Path) -> Path:
    cooling_conditions = [
        ("Temp. entree eau utilisation", "C", "12.0"),
        ("Temp. sortie eau utilisation", "C", "7.0"),
        ("Glycol cote utilisation", "%", "0"),
        ("Temp. air exterieur source", "C", "35.0"),
        ("Humidite relative air source", "%", "40"),
        ("Pourcentage de charge", "%", "100"),
    ]
    cooling_perf = [
        ("Puissance frigorifique", "kW", "210.0"),
        ("Debit eau utilisateur", "l/h", "36000"),
        ("Perte de charge utilisateur", "kPa", "45"),
        ("Puissance absorbee compresseurs", "kW", "72.0"),
        ("Courant absorbe compresseurs", "A", "110.0"),
        ("Puissance absorbee totale", "kW", "75.0"),
        ("Courant absorbe total", "A", "118.0"),
        ("EER", "W/W", "2.80"),
        ("EER UNI EN 14511", "W/W", "2.78"),
        ("SEER", "Wh/Wh", "4.10"),
    ]
    general = [
        ("Max courant absorbe (FLA)", "A", "180"),
        ("Courant de demarrage (LRA)", "A", "210"),
        ("Niveau de puissance acoustique Lw", "dB(A)", "88"),
        ("Niveau de pression acoustique Lp", "dB(A)", "60"),
        ("Debit d'air source", "m3/h", "52000"),
        ("Nombre de ventilateurs", "", "4"),
        ("Refrigerant", "", "R454B"),
        ("GWP", "", "466"),
        ("Poids sans options", "kg", "900"),
        ("Alimentation", "", "400 / 3+N / 50"),
    ]

    story = _build_story(
        designation="VLS202CS0A B000CE000I00220 0000000I000000000000",
        cooling_conditions=cooling_conditions,
        heating_conditions=None,
        cooling_perf=cooling_perf,
        heating_perf=None,
        general=general,
    )
    SimpleDocTemplate(str(path), pagesize=A4).build(story)
    return path
