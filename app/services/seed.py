"""Demo brand charts. These are ILLUSTRATIVE generic charts, not real brand data -
replace with real, licensed size charts via POST /v1/brands."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Brand, SizeChart

_MEN = [
    ("S", (86, 94), (71, 79), (40, 42.5)),
    ("M", (94, 102), (79, 87), (42.5, 45)),
    ("L", (102, 110), (87, 95), (45, 47.5)),
    ("XL", (110, 118), (95, 103), (47.5, 50)),
    ("XXL", (118, 126), (103, 111), (50, 52.5)),
]
_WOMEN = [
    ("XS", (78, 84), (60, 66), (35, 36.5)),
    ("S", (84, 90), (66, 72), (36.5, 38)),
    ("M", (90, 96), (72, 78), (38, 39.5)),
    ("L", (96, 102), (78, 84), (39.5, 41)),
    ("XL", (102, 108), (84, 90), (41, 42.5)),
]


def _entries(rows, shift: float = 0.0):
    return [
        {
            "label": label,
            "chest": [c[0] + shift, c[1] + shift],
            "waist": [w[0] + shift, w[1] + shift],
            "shoulder": list(s),
        }
        for label, c, w, s in rows
    ]


async def seed_demo(session: AsyncSession) -> None:
    if (await session.execute(select(Brand).limit(1))).scalar_one_or_none():
        return
    # "demo-urban" runs true to size; "demo-slim" runs ~4cm smaller (a classic cause of returns).
    for slug, name, shift, fit in (
        ("demo-urban", "Demo Urban (sample data)", 0.0, "regular"),
        ("demo-slim", "Demo Slim (sample data)", -4.0, "slim"),
    ):
        b = Brand(slug=slug, name=name)
        for gender, rows in (("male", _MEN), ("female", _WOMEN)):
            b.charts.append(
                SizeChart(category="tshirt", gender=gender, fit_type=fit, entries=_entries(rows, shift))
            )
        session.add(b)
    await session.commit()
