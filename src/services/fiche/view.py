"""View model of the INVENIO selection fiche.

The fiche is laid out as fixed A4 pages (cover, contents, synthesis,
technical data, options, description, plans, implantation, contacts, back
cover). Every page number is known here, before rendering, so the document
looks the same in WeasyPrint, in the in-app preview and in the browser's
print dialog, none of which has to resolve cross-references.

All computations live here and are unit-tested; the Jinja template only
places pre-formatted strings.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.services.fiche import format as fmt
from src.services.fiche.resources import font_widths, france_map, range_documentation

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Plan:
    name: str
    data_url: str


@dataclass(frozen=True)
class FicheInputs:
    record: dict[str, Any]
    generated_at: datetime
    document_reference: str
    project_name: str | None = None
    contacts: dict[str, Any] | None = None
    catalog_options: tuple[dict[str, Any], ...] = ()
    selected_option_codes: tuple[str, ...] = ()
    plans: tuple[Plan, ...] = ()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return "".join(c for c in folded if not unicodedata.combining(c)).lower()


def _num(value: Any) -> float | None:
    return float(value) if fmt.is_number(value) else None


def _pct(value: float, low: float, high: float) -> float:
    return round((value - low) / (high - low) * 100, 2)


# ---------------------------------------------------------------------------
# Icons (24 x 24 stroke icons, drawn for the fiche)
# ---------------------------------------------------------------------------

ICONS = {
    "drop": '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/><path d="M9.5 14.5c.3 1.4 1.3 2.3 2.5 2.5"/>',
    "scroll": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5a4.5 4.5 0 1 1-4.5 4.5M12 10.2a1.8 1.8 0 1 1-1.8 1.8"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6l7-3z"/><path d="M9 12l2 2 4-4"/>',
    "hydraulique": '<path d="M12 3C12 3 5.5 10.5 5.5 14.5a6.5 6.5 0 0 0 13 0C18.5 10.5 12 3 12 3z"/>',
    "regulation": '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M9 20h6M12 16v4M7.5 9.5l2.5 2-2.5 2M12.5 13.5h4"/>',
    "acoustique": '<path d="M4 10v4h3.5L12 18V6L7.5 10H4z"/><path d="M15.5 9.2a4 4 0 0 1 0 5.6M18 7a7 7 0 0 1 0 10"/>',
    "electrique": '<path d="M13 3L6 13.5h5L10 21l7-10.5h-5L13 3z"/>',
    "aeraulique": '<circle cx="12" cy="12" r="1.6"/><path d="M12 10.4C11 7 12 4.5 14.5 4.5c2 0 2.5 2.4.5 4.2M13.4 12.8c3.4 1 5.6 3 4.6 5-1 1.8-3.3 1-4.2-1.6M10.4 12.6c-2.6 2.4-5.2 2.8-6 1-.8-1.9 1.2-3.3 3.8-3"/>',
    "accessoires": '<rect x="4.5" y="4.5" width="15" height="15" rx="1.5"/><path d="M12 8.5v7M8.5 12h7"/>',
}


def icon_svg(name: str, stroke: str, css_class: str) -> str:
    return (
        f'<svg class="{css_class}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" '
        f'fill="none" stroke="{stroke}" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS.get(name, ICONS["accessoires"])}</svg>'
    )


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

_FAMILY_KIND = {
    "PAC": "Pompe à chaleur air / eau",
    "GEG": "Groupe d’eau glacée air / eau",
}


def _kind(record: dict[str, Any], gamme: dict[str, Any] | None) -> str:
    unit_type = str(record.get("type") or "")
    if gamme and unit_type:
        kind = _dict(gamme.get("kinds")).get(unit_type[:1].upper())
        if kind:
            return str(kind)
    return _FAMILY_KIND.get(str(record.get("family") or "").upper(), "Unité air / eau")


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def _duty(title: str, perf: dict[str, Any], cond: dict[str, Any], rows: list[tuple[str, str]]):
    return {
        "title": title,
        "power": fmt.number(perf.get("power_kW")),
        "air": fmt.number(cond.get("air_temp_C"), "°C"),
        "water_in": fmt.number(cond.get("water_in_C"), "°C"),
        "water_out": fmt.number(cond.get("water_out_C"), "°C"),
        "rows": [(label, value) for label, value in rows if value != fmt.DASH],
    }


def _humidity_glycol(cond: dict[str, Any]) -> str:
    humidity, glycol = cond.get("air_humidity_percent"), cond.get("glycol_percent")
    if humidity is None and glycol is None:
        return fmt.DASH
    return f"{fmt.number(humidity, '%')} · {fmt.number(glycol, '%')}"


def _balance(title: str, inputs: list[tuple[str, float, str]], output: tuple[str, float]):
    total = output[1]
    return {
        "title": title,
        "inputs": [
            {
                "label": label,
                "value": fmt.number(value, "kW", 1),
                "width": round(value / total * 100, 2),
                "kind": kind,
            }
            for label, value, kind in inputs
        ],
        "output": {"label": output[0], "value": fmt.number(output[1], "kW", 1)},
    }


def _balances(cool: dict[str, Any], heat: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    qc, pc = _num(cool.get("power_kW")), _num(cool.get("total_power_kW"))
    if qc and pc and qc > 0 and pc > 0:
        result.append(
            _balance(
                "Partie froide",
                [("Chaleur extraite de l’eau", qc, "amb"), ("Électricité", pc, "elec")],
                ("Chaleur rejetée à l’air", qc + pc),
            )
        )
    qh, ph = _num(heat.get("power_kW")), _num(heat.get("total_power_kW"))
    if qh and ph and qh > ph > 0:
        result.append(
            _balance(
                "Partie chaude",
                [("Électricité", ph, "elec"), ("Énergie captée sur l’air", qh - ph, "amb")],
                ("Chaleur restituée à l’eau", qh),
            )
        )
    return result


ERP_STEPS = ("A+++", "A++", "A+", "A", "B", "C", "D")


def _erp(heat: dict[str, Any]) -> dict[str, Any] | None:
    seasonal = str(heat.get("seasonal_class") or "").strip()
    if seasonal not in ERP_STEPS:
        return None
    parts = []
    if heat.get("eta_s_percent") is not None:
        parts.append(f"Rendement saisonnier ηs {fmt.number(heat.get('eta_s_percent'), '%')}")
    if heat.get("scop") is not None:
        parts.append(f"SCOP {fmt.number(heat.get('scop'))}")
    parts.append("classe issue de la sélection GALLETTI")
    return {"steps": [(step, step == seasonal) for step in ERP_STEPS], "caption": " · ".join(parts)}


# ---------------------------------------------------------------------------
# Technical data
# ---------------------------------------------------------------------------


def _acoustic(general: dict[str, Any], acoustic: dict[str, Any]) -> dict[str, Any] | None:
    lw = _num(general.get("sound_power_lw_dBA"))
    q = _num(acoustic.get("directionality_factor"))
    given = _num(acoustic.get("free_field_distance_m"))
    lp_given = _num(general.get("sound_pressure_lp_dBA"))
    if lw is None:
        return None
    rows = []
    if q and q > 0:
        distances = sorted({5.0, 10.0, 20.0} | ({given} if given and given > 0 else set()))
        for r in distances:
            lp = lw + 10 * math.log10(q / (4 * math.pi * r * r))
            is_given = given is not None and abs(r - given) < 1e-6
            if is_given and lp_given is not None:
                lp = lp_given
            rows.append(
                {
                    "label": f"Pression Lp à {fmt.number(r)} m",
                    "value": fmt.number(round(lp), "dB(A)"),
                    "bar": round(max(0.0, min(1.0, (lp - 35) / 45)) * 34, 1),
                    "given": is_given,
                }
            )
        caption = (
            f"Pression acoustique en champ libre, facteur de directivité Q = {fmt.number(q)}. "
            + (
                f"La valeur à {fmt.number(given)} m est celle de la sélection ; les autres "
                "distances en sont déduites (Lp = Lw + 10 log Q / 4πr²)."
                if given
                else "Valeurs déduites de la puissance acoustique (Lp = Lw + 10 log Q / 4πr²)."
            )
        )
    else:
        if lp_given is not None:
            rows.append(
                {
                    "label": "Pression Lp (sélection)",
                    "value": fmt.number(lp_given, "dB(A)"),
                    "bar": round(max(0.0, min(1.0, (lp_given - 35) / 45)) * 34, 1),
                    "given": True,
                }
            )
        caption = "Facteur de directivité non communiqué : pas d’extrapolation à d’autres distances."
    return {"lw": fmt.number(lw, "dB(A)"), "rows": rows, "caption": caption}


def _rangebar(label: str, limits: list[float], marks: list[tuple[float | None, str, str]]):
    low, high = float(limits[0]), float(limits[1])
    margin = (high - low) * 0.09
    axis = (low - margin, high + margin)
    return {
        "label": label,
        "fill_left": _pct(low, *axis),
        "fill_width": round(_pct(high, *axis) - _pct(low, *axis), 2),
        "low": fmt.number(low, "°C"),
        "high": fmt.number(high, "°C"),
        "low_at": _pct(low, *axis),
        "high_at": _pct(high, *axis),
        "marks": [
            {"at": _pct(min(max(v, axis[0]), axis[1]), *axis), "label": text, "kind": kind}
            for v, text, kind in marks
            if v is not None
        ],
    }


def _envelope(gamme, cond_c, cond_h, model: str) -> dict[str, Any] | None:
    envelope = _dict(_dict(gamme).get("envelope"))
    air, water = envelope.get("air_C"), envelope.get("water_C")
    if not (isinstance(air, list) and isinstance(water, list)):
        return None

    def mark(cond: dict[str, Any], key: str, name: str, kind: str):
        value = _num(cond.get(key))
        return (value, f"{name} {fmt.number(value, '°C')}", kind)

    return {
        "title": f"Plage de fonctionnement · gamme {model}",
        "bars": [
            _rangebar(
                "Air extérieur",
                air,
                [mark(cond_c, "air_temp_C", "Froid", "c"), mark(cond_h, "air_temp_C", "Chaud", "h")],
            ),
            _rangebar(
                "Eau produite",
                water,
                [mark(cond_c, "water_out_C", "Froid", "c"), mark(cond_h, "water_out_C", "Chaud", "h")],
            ),
        ],
        "source": str(envelope.get("source") or ""),
    }


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

_FAMILIES = (
    ("hydraulique", "Hydraulique", ("pompe", "reservoir", "ballon", "antigel", "hydraul", "vanne", "filtre", "eau", "glycol")),
    ("regulation", "Régulation et communication", ("communic", "reglage", "regul", "carte", "supervis", "gtc", "afficheur", "commande")),
    ("acoustique", "Acoustique", ("acoust", "bruit", "silenc", "capot", "phoni")),
    ("electrique", "Électrique", ("electr", "alimentation", "tableau", "condensat", "demarr", "puissance")),
    ("aeraulique", "Aéraulique et batterie", ("batterie", "ventil", "aeraul", "air", "ailette")),
)
_OTHER_FAMILY = ("accessoires", "Accessoires")

_CATEGORY_LABELS = {
    "pompe eau cote utilisateur": "Pompe à eau côté utilisateur",
    "reservoir tampon": "Réservoir tampon",
    "kit antigel": "Kit antigel",
    "reglage": "Réglage",
    "electrique": "Électrique",
}


def _category_label(category: str) -> str:
    label = _CATEGORY_LABELS.get(_fold(category).strip())
    if label:
        return label
    category = category.strip()
    return category[:1].upper() + category[1:] if category else "Divers"


def _family_of(category: str) -> tuple[str, str]:
    folded = _fold(category)
    for key, name, keywords in _FAMILIES:
        if any(word in folded for word in keywords):
            return key, name
    return _OTHER_FAMILY


def _is_pump(option: dict[str, Any]) -> bool:
    return "pompe" in _fold(str(option.get("category") or "")) and "absent" not in _fold(
        str(option.get("label") or "")
    )


# Heights (mm) used to paginate the options across fixed pages, measured on
# WeasyPrint's layout: the options area runs from 67 mm to 275 mm on the page,
# a text line is 4.55 mm (8.6 pt x 1.5), a row adds 2.8 mm of padding and rule.
_OPTIONS_BUDGET_MM = 205.0
_FAMILY_HEADER_MM = 8.8
_FAMILY_GAP_MM = 5.0
_CATEGORY_ROW_MM = 7.2
_LINE_MM = 4.55


_TEXT_COLUMN_MM = 100.0  # 174 mm table minus the mark, code, price and state columns
_PT_TO_MM = 25.4 / 72


def text_lines(text: str, size_pt: float, width_mm: float, weight: int = 400) -> int:
    """Number of lines ``text`` takes once wrapped in a column (Montserrat metrics)."""

    widths = font_widths()[str(weight)]
    em = size_pt * _PT_TO_MM
    space = widths.get(" ", 0.27) * em
    lines, current = 1, 0.0
    for word in text.split():
        word_width = sum(widths.get(char, 0.65) for char in word) * em
        if current == 0.0:
            current = word_width
        elif current + space + word_width <= width_mm:
            current += space + word_width
        else:
            lines += 1
            current = word_width
    return lines


def _option_height(option: dict[str, Any]) -> float:
    weight = 600 if option.get("selected") else 400
    label_lines = text_lines(option["label"], 8.6, _TEXT_COLUMN_MM, weight)
    desc = option.get("description") or ""
    desc_lines = text_lines(desc, 7.4, _TEXT_COLUMN_MM) if desc else 0
    return 2.8 + _LINE_MM * (label_lines + desc_lines)


def _options(
    catalog: tuple[dict[str, Any], ...],
    record_options: list[Any],
    selected_codes: tuple[str, ...],
):
    """Group the options by family and paginate them.

    Returns (pages, summary, selected_pump).
    """

    source = [o for o in catalog if isinstance(o, dict)]
    from_catalog = bool(source)
    if not source:
        source = [
            o
            for o in record_options
            if isinstance(o, dict) and o.get("category") not in (None, "", "designation")
        ]
    if selected_codes:
        wanted = set(selected_codes)
    else:
        wanted = {
            str(o.get("code"))
            for o in record_options
            if isinstance(o, dict) and o.get("selected") and o.get("code")
        }

    families: dict[str, dict[str, Any]] = {}
    order = [key for key, _, _ in _FAMILIES] + [_OTHER_FAMILY[0]]
    any_price = False
    for raw in source:
        category = str(raw.get("category") or "")
        key, name = _family_of(category)
        price = _num(raw.get("price_eur"))
        any_price = any_price or price is not None
        option: dict[str, Any] = {
            "code": str(raw.get("code") or ""),
            "label": str(raw.get("label") or "").strip() or fmt.DASH,
            "description": str(raw.get("description") or "").strip(),
            "price": fmt.number(price, "€") if price is not None else fmt.DASH,
            "selected": str(raw.get("code") or "") in wanted,
            "raw": raw,
        }
        family = families.setdefault(
            key,
            {"key": key, "name": name, "icon": key, "categories": {}, "selected": 0, "total": 0},
        )
        family["categories"].setdefault(_category_label(category), []).append(option)
        family["total"] += 1
        family["selected"] += int(option["selected"])

    ordered = [families[key] for key in order if key in families]

    pages: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    used = 0.0
    for family in ordered:
        meta = {
            "name": family["name"],
            "icon": family["icon"],
            "count": (
                f"{family['selected']} retenue{'s' if family['selected'] > 1 else ''}"
                f" sur {family['total']}"
            ),
        }
        block: dict[str, Any] | None = None
        started = False
        for category, options in family["categories"].items():
            rows: list[tuple[str, Any, float]] = [("cat", category, _CATEGORY_ROW_MM)]
            rows += [("opt", option, _option_height(option)) for option in options]
            for index, (kind, payload, height) in enumerate(rows):
                need = height
                if kind == "cat" and index + 1 < len(rows):
                    need += rows[index + 1][2]  # keep a category with its first option
                if block is None:
                    need += _FAMILY_HEADER_MM + _FAMILY_GAP_MM
                if current and used + need > _OPTIONS_BUDGET_MM:
                    pages.append(current)
                    current, used, block = [], 0.0, None
                if block is None:
                    block = {"family": meta, "continued": started, "rows": []}
                    current.append(block)
                    used += _FAMILY_HEADER_MM + _FAMILY_GAP_MM
                    started = True
                if kind == "cat":
                    block["rows"].append({"type": "cat", "label": payload})
                else:
                    block["rows"].append({"type": "opt", **{k: v for k, v in payload.items() if k != "raw"}})
                used += height
    if current or not pages:
        pages.append(current)

    total = sum(f["total"] for f in ordered)
    selected = sum(f["selected"] for f in ordered)
    pump = next(
        (o["raw"] for f in ordered for opts in f["categories"].values() for o in opts if o["selected"] and _is_pump(o["raw"])),
        None,
    )
    summary = {
        "total": total,
        "selected": selected,
        "show_price": any_price,
        "source": "Catalogue GALLETTI" if from_catalog else "Options décodées de la désignation",
    }
    return pages, summary, pump


# ---------------------------------------------------------------------------
# Implantation
# ---------------------------------------------------------------------------


def _implantation(record, gamme, cool, heat) -> dict[str, Any] | None:
    doc = _dict(_dict(gamme).get("implantation"))
    if not doc:
        return None
    general = _dict(record.get("general"))
    size = str(record.get("size") or "")
    unit_type = str(record.get("type") or "")
    key = f"{size}{unit_type[:1].upper()}"
    clearances = _dict(_dict(doc.get("clearances")).get(key))
    rows = []
    if clearances:
        for field_, label in (
            ("maintenance_b_m", "Zone de maintenance (B)"),
            ("maintenance_c_m", "Zone de maintenance (C)"),
            ("safety_d_m", "Zone de sécurité R290 (D)"),
        ):
            if clearances.get(field_) is not None:
                rows.append((label, fmt.number(clearances[field_], "m")))
    refrigerant = str(general.get("refrigerant") or "").upper()
    safety = doc.get("refrigerant_safety") if refrigerant == "R290" else None

    site = []
    if general.get("weight_kg") is not None:
        site.append(f"Support dimensionné pour la masse de la machine : {fmt.number(general['weight_kg'], 'kg')}.")
    if general.get("supply"):
        electrical = f"Alimentation {fmt.supply(general['supply'])}"
        if general.get("max_current_A") is not None:
            electrical += f" ; courant maximal {fmt.number(general['max_current_A'], 'A')}"
        if general.get("starting_current_A") is not None:
            electrical += f", démarrage {fmt.number(general['starting_current_A'], 'A')}"
        site.append(electrical + ".")
    flows = []
    if cool.get("water_flow_lph") is not None:
        flows.append(f"{fmt.number(cool['water_flow_lph'], 'l/h')} en froid")
    if heat.get("water_flow_lph") is not None:
        flows.append(f"{fmt.number(heat['water_flow_lph'], 'l/h')} en chaud")
    if flows:
        site.append("Débit d’eau à assurer : " + ", ".join(flows) + ".")
    if rows:
        site.append("Dégagements de maintenance libres de tout obstacle (zones B et C).")

    title_type = unit_type[:1].upper()
    return {
        "title": f"Dégagements et zones · {record.get('model', '')} {size} {title_type}".strip(),
        "rows": rows,
        "safety_distance": fmt.number(clearances.get("safety_d_m"), "m") if clearances.get("safety_d_m") is not None else None,
        "caption": str(doc.get("source") or "") if rows else str(doc.get("missing") or ""),
        "safety": list(safety) if isinstance(safety, list) else [],
        "site": site,
    }


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

_ROLES = (
    ("tci", "TCI", "Technico-commercial itinérant"),
    ("tcs", "TCS", "Technico-commercial sédentaire"),
    ("solution", "SOLUTION", "Solution Habitat"),
)


def _initials(name: str) -> str:
    words = [w for w in re.split(r"[\s-]+", name) if w]
    return "".join(w[0] for w in words[:2]).upper()


def _map_svg(code: str) -> str:
    data = france_map()
    width, height = data["width"], data["height"]
    paths, highlight = [], ""
    for dep in data["departments"]:
        if dep["code"] == code:
            highlight = (
                f'<path d="{dep["d"]}" fill="#032d59" stroke="#ffffff" stroke-width="0.9" '
                'stroke-linejoin="round"/>'
            )
        else:
            paths.append(f'<path d="{dep["d"]}"/>')
    return (
        f'<svg class="map" viewBox="-4 -4 {width + 8:.0f} {height + 8:.0f}" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<g fill="#e8edf3" stroke="#9aa8b6" stroke-width="0.55" stroke-linejoin="round">'
        + "".join(paths)
        + "</g>"
        + highlight
        + "</svg>"
    )


def _contacts(contacts: dict[str, Any] | None) -> dict[str, Any] | None:
    contacts = _dict(contacts)
    code = str(contacts.get("department") or "").strip().upper()
    people = []
    for key, role, title in _ROLES:
        person = _dict(contacts.get(key))
        if not person.get("name"):
            continue
        people.append(
            {
                "role": role,
                "title": title,
                "name": str(person["name"]),
                "initials": _initials(str(person["name"])),
                "email": str(person.get("email") or ""),
                "phone": str(person.get("phone") or ""),
            }
        )
    if not code or not people:
        return None
    name = next((d["name"] for d in france_map()["departments"] if d["code"] == code), "")
    return {
        "code": code,
        "name": name,
        "map": _map_svg(code),
        "people": people,
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_view(inputs: FicheInputs) -> dict[str, Any]:
    record = inputs.record
    model = str(record.get("model") or "").strip()
    size = str(record.get("size") or "").strip()
    unit_type = str(record.get("type") or "").strip()
    machine = " ".join(part for part in (model, size, unit_type) if part) or "Machine"
    gamme = range_documentation(model)
    project = (inputs.project_name or "").strip() or None

    perf = _dict(record.get("performance"))
    cond = _dict(record.get("conditions"))
    cool, heat = _dict(perf.get("cooling")), _dict(perf.get("heating"))
    cond_c, cond_h = _dict(cond.get("cooling")), _dict(cond.get("heating"))
    general = _dict(record.get("general"))
    acoustic = _dict(record.get("acoustic"))
    norm = _dict(record.get("norm"))
    has_heating = heat.get("power_kW") is not None
    has_cooling = cool.get("power_kW") is not None

    # --- cover ---------------------------------------------------------------
    figures = []
    if has_cooling:
        figures.append(("FROID", fmt.number(cool.get("power_kW")), "kW"))
    if has_heating:
        figures.append(("CHAUD", fmt.number(heat.get("power_kW")), "kW"))
    if has_heating and (heat.get("cop") is not None or heat.get("scop") is not None):
        figures.append(("COP · SCOP", f"{fmt.number(heat.get('cop'))} · {fmt.number(heat.get('scop'))}", ""))
    elif cool.get("eer") is not None or cool.get("seer") is not None:
        figures.append(("EER · SEER", f"{fmt.number(cool.get('eer'))} · {fmt.number(cool.get('seer'))}", ""))
    if general.get("sound_power_lw_dBA") is not None:
        figures.append(("ACOUSTIQUE", fmt.number(general.get("sound_power_lw_dBA")), "dB(A)"))

    photo = str(_dict(gamme).get("photo") or "") or None
    cover = {
        "project": project,
        "title": project or f"Sélection {model} {size}".strip(),
        "title_long": len(project or "") > 24,
        "model": model,
        "size": size,
        "range": (str(_dict(gamme).get("range_label") or f"Gamme {model}")).upper(),
        "kind": _kind(record, gamme),
        "version": " · ".join(p for p in (f"VERSION {unit_type}" if unit_type else "", str(general.get("refrigerant") or "")) if p),
        "figures": figures,
        "reference": str(record.get("designation_code") or "").strip(),
        "photo": photo,
    }

    # --- synthesis -----------------------------------------------------------
    duties = []
    if has_cooling or not has_heating:
        duties.append(
            _duty(
                "Partie froide",
                cool,
                cond_c,
                [
                    ("EER", fmt.number(cool.get("eer"))),
                    ("EER selon UNI", fmt.number(cool.get("eer_uni"))),
                    ("SEER", fmt.number(cool.get("seer"))),
                    ("Débit d’eau", fmt.number(cool.get("water_flow_lph"), "l/h")),
                    ("Perte de charge échangeur", fmt.number(cool.get("pressure_drop_kPa"), "kPa")),
                    ("Humidité · glycol", _humidity_glycol(cond_c)),
                ],
            )
        )
    if has_heating:
        duties.append(
            _duty(
                "Partie chaude",
                heat,
                cond_h,
                [
                    ("COP", fmt.number(heat.get("cop"))),
                    ("COP selon UNI", fmt.number(heat.get("cop_uni"))),
                    ("SCOP", fmt.number(heat.get("scop"))),
                    ("Débit d’eau", fmt.number(heat.get("water_flow_lph"), "l/h")),
                    ("Perte de charge échangeur", fmt.number(heat.get("pressure_drop_kPa"), "kPa")),
                    ("Humidité · glycol", _humidity_glycol(cond_h)),
                ],
            )
        )
    norm_version = norm.get("uni_en_14511_version")
    synthese = {
        "lede": (
            f"Performances au point de sélection, calculées selon {norm_version}."
            if norm_version
            else "Performances au point de sélection."
        ),
        "duties": duties,
        "no_heating": not has_heating,
        "balances": _balances(cool, heat),
        "erp": _erp(heat) if has_heating else None,
    }

    # --- technical data ------------------------------------------------------
    columns = [label for label, present in (("Froid", has_cooling or not has_heating), ("Chaud", has_heating)) if present]

    def pair(key: str, unit: str) -> list[str]:
        values = []
        if "Froid" in columns:
            values.append(fmt.number(cool.get(key), unit))
        if "Chaud" in columns:
            values.append(fmt.number(heat.get(key), unit))
        return values

    electrical_rows = [
        ("Puissance absorbée totale", pair("total_power_kW", "kW")),
        ("dont compresseurs", pair("compressors_power_kW", "kW")),
        ("Intensité absorbée totale", pair("total_current_A", "A")),
        ("dont compresseurs", pair("compressors_current_A", "A")),
        ("Alimentation", [fmt.supply(general.get("supply"))]),
        (
            "Courant maximal (FLA) · démarrage",
            [f"{fmt.number(general.get('max_current_A'), 'A')} · {fmt.number(general.get('starting_current_A'), 'A')}"],
        ),
    ]

    options_pages, options_summary, pump = _options(
        inputs.catalog_options, list(record.get("options") or []), inputs.selected_option_codes
    )

    pump_rows = [("Machine de base, sans pompe", [fmt.DASH, fmt.DASH])]
    pump_known = False
    if pump:
        current = pump.get("current_A")
        pressure = pump.get("available_pressure_kPa")
        pump_known = current is not None or pressure is not None
        pump_rows.append(
            (f"{pump.get('label')} (retenue)", [fmt.number(current, "A"), fmt.number(pressure, "kPa")])
        )
    else:
        pump_rows.append(("Aucune pompe retenue", [fmt.DASH, fmt.DASH]))

    technique = {
        "columns": columns,
        "electrical": electrical_rows,
        "acoustic": _acoustic(general, acoustic),
        "envelope": _envelope(gamme, cond_c, cond_h, model),
        "aeraulic": [
            ("Débit d’air", fmt.number(general.get("source_air_flow_m3h"), "m³/h")),
            ("Ventilateurs", fmt.number(general.get("source_fans_count"))),
        ],
        "refrigerant": [
            (
                "Réfrigérant · GWP",
                f"{fmt.number(general.get('refrigerant'))} · {fmt.number(general.get('gwp'))}",
            ),
            ("Poids", fmt.number(general.get("weight_kg"), "kg")),
        ],
        "pump_rows": pump_rows,
        "pump_missing": not pump_known,
    }

    # --- description, implantation, contacts --------------------------------
    description = None
    if gamme and gamme.get("description"):
        description = {
            "highlights": [
                {"icon": icon_svg(str(h.get("icon")), "#032d59", "aic"), "title": h.get("title", ""), "text": h.get("text", "")}
                for h in gamme.get("highlights") or []
            ],
            "chapters": gamme["description"],
            "sources": gamme.get("description_sources", ""),
        }
    implantation = _implantation(record, gamme, cool, heat)
    contacts = _contacts(inputs.contacts)

    # --- pages -------------------------------------------------------------
    footer = f"{project} · {machine}" if project else machine
    pages: list[dict[str, Any]] = [{"kind": "cover"}, {"kind": "toc"}]
    toc: list[dict[str, Any]] = []

    def section(kind: str, title: str, note: str, **data: Any) -> dict[str, Any]:
        number = f"{len(toc) + 1:02d}"
        toc.append({"no": number, "title": title, "page": len(pages) + 1, "kind": kind})
        return {"kind": kind, "section": {"no": number, "title": title, "note": note}, **data}

    pages.append(section("synthese", "Synthèse de la sélection", machine, data=synthese))
    pages.append(section("technique", "Données techniques", machine, data=technique))
    options_entry = section("options", "Options et accessoires", machine, data=options_pages[0], summary=options_summary)
    options_page_no = len(pages) + 1
    pages.append(options_entry)
    for index, chunk in enumerate(options_pages[1:], 2):
        pages.append(
            {
                "kind": "options",
                "section": {**options_entry["section"], "note": f"{machine} · suite {index}/{len(options_pages)}"},
                "data": chunk,
                "summary": options_summary,
                "continued": True,
            }
        )
    if description:
        pages.append(section("description", "Descriptif de la machine", f"Gamme {model}", data=description))
    if inputs.plans:
        first = True
        for plan in inputs.plans:
            if first:
                pages.append(section("plans", "Plans et dimensions", f"Taille {size}", plan=plan))
                first = False
            else:
                pages.append(
                    {"kind": "plans", "section": {**pages[-1]["section"]}, "plan": plan, "continued": True}
                )
    if implantation:
        pages.append(section("implantation", "Implantation", machine, data=implantation))
    if contacts:
        pages.append(section("contacts", "Vos contacts France Air", f"Département {contacts['code']}", data=contacts))
    pages.append({"kind": "back"})

    for number, page in enumerate(pages, 1):
        page.setdefault("continued", False)
        page["number"] = number
        page["folio"] = f"{number:02d}"

    return {
        "machine": machine,
        "project": project,
        "footer": footer,
        "title": f"{project} — {machine}" if project else f"Fiche de sélection — {machine}",
        "edition": f"Édition du {fmt.long_date(inputs.generated_at)}",
        "edition_short": fmt.short_date(inputs.generated_at),
        "document_reference": inputs.document_reference,
        "cover": cover,
        "pages": pages,
        "toc": toc,
        "options_page": options_page_no,
        "family_icons": {key: icon_svg(key, "#ffffff", "ic") for key in ICONS},
        "weight": fmt.number(general.get("weight_kg"), "kg"),
        "legal": (
            f"Document édité le {fmt.long_date(inputs.generated_at)} à partir d’une sélection "
            "GALLETTI. Les valeurs sont données au point de fonctionnement indiqué ; se référer à la "
            "documentation constructeur pour toute utilisation contractuelle."
        ),
    }
