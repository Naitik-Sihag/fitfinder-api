"""Size recommendation: match body measurements against a brand's size chart.

Each size is scored by how far the (fit-adjusted) body measurements fall outside that size's
published range, weighted per measurement. Lowest penalty wins. Penalties are converted to a
return-risk probability with a logistic curve whose parameters should be *learned* from the
`feedback` table once enough purchase outcomes exist (see README).
"""

import math
from dataclasses import dataclass

from app.schemas import (
    BodyMeasurements,
    ChartEntry,
    FitNote,
    FitPreference,
    RecommendResponse,
    SizeScore,
)

MODEL_VERSION = "rules-0.1"

# Chest drives t-shirt/shirt fit most; shoulder next; waist/hip matter less for tops.
WEIGHTS = {"chest": 1.0, "shoulder": 0.7, "waist": 0.5, "hip": 0.25}
# How much "ease" the wearer wants, in cm added to the body measurement before matching.
FIT_OFFSET = {FitPreference.slim: -2.0, FitPreference.regular: 0.0, FitPreference.relaxed: 3.0}
SNUG_TOL = 2.0  # cm tolerance before a measurement is called snug/loose
RISK_MIDPOINT = 3.0
RISK_STEEPNESS = 0.9


@dataclass
class _Scored:
    entry: ChartEntry
    penalty: float
    notes: list[FitNote]


def _dist_outside(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return value - lo  # negative: body smaller than size
    if value > hi:
        return value - hi  # positive: body larger than size
    return 0.0


def _risk(penalty: float) -> float:
    """Logistic mapping penalty -> P(size-related return). Floor ~5% (some returns are unavoidable)."""
    p = 1 / (1 + math.exp(-RISK_STEEPNESS * (penalty - RISK_MIDPOINT)))
    return round(0.05 + 0.90 * p, 3)


def _score(entry: ChartEntry, body: BodyMeasurements, offset: float) -> _Scored:
    penalty, notes = 0.0, []
    for name, w in WEIGHTS.items():
        rng = getattr(entry, name)
        val = getattr(body, name)
        if rng is None or val is None:
            continue
        # Ease applies to girths; shoulder width is left as-is.
        eff = val + (offset if name != "shoulder" else 0.0)
        d = _dist_outside(eff, *rng)
        penalty += w * abs(d)
        if d > SNUG_TOL:
            verdict = "snug"  # body bigger than size -> tight
        elif d < -SNUG_TOL:
            verdict = "loose"
        else:
            verdict = "good"
        notes.append(
            FitNote(measurement=name, body_cm=round(val, 1), size_range_cm=tuple(rng), verdict=verdict)
        )
    return _Scored(entry, penalty, notes)


def recommend(
    entries: list[ChartEntry],
    body: BodyMeasurements,
    preference: FitPreference,
    *,
    source: str,
    uncertainty_cm: float = 0.0,
) -> RecommendResponse:
    if not entries:
        raise ValueError("size chart has no entries")
    offset = FIT_OFFSET[preference]
    # Order by chest so ties resolve towards the larger size (safer: shrink > stretch for returns).
    ordered = sorted(entries, key=lambda e: e.chest[0])
    scored = [_score(e, body, offset) for e in ordered]
    ranked = sorted(scored, key=lambda s: (round(s.penalty, 3), -ordered.index(s.entry)))
    best, runner = ranked[0], (ranked[1] if len(ranked) > 1 else None)

    margin = (runner.penalty - best.penalty) if runner else 5.0
    # Confidence: wide margin over runner-up is good; measurement uncertainty subtracts.
    conf = 1 / (1 + math.exp(-(0.8 * margin - 0.25 * uncertainty_cm + 0.2)))
    conf = round(min(max(conf, 0.05), 0.98), 3)

    risk = _risk(best.penalty + 0.15 * uncertainty_cm)
    advice = _advice(best, runner, preference, conf)
    return RecommendResponse(
        recommended_size=best.entry.label,
        confidence=conf,
        return_risk=risk,
        fit_notes=best.notes,
        alternatives=[
            SizeScore(size=s.entry.label, penalty=round(s.penalty, 2), return_risk=_risk(s.penalty))
            for s in ranked[1:3]
        ],
        measurements_used=body,
        measurement_source=source,
        model_version=MODEL_VERSION,
        advice=advice,
    )


def _advice(best: _Scored, runner: _Scored | None, pref: FitPreference, conf: float) -> str:
    msg = f"Size {best.entry.label} is your best match for a {pref.value} fit."
    if runner and abs(best.penalty - runner.penalty) < 1.0:
        msg += f" You are between sizes - {runner.entry.label} is almost as good."
        msg += " Choose the larger for a looser feel, the smaller for a closer fit."
    elif conf < 0.5:
        msg += " Confidence is low; add exact measurements or a body scan to improve accuracy."
    return msg
