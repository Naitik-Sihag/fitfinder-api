from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Brand, SizeChart
from app.schemas import BrandIn, BrandOut
from app.security import require_api_key

router = APIRouter(prefix="/v1/brands", tags=["brands"], dependencies=[Depends(require_api_key)])


def _out(b: Brand) -> BrandOut:
    return BrandOut(slug=b.slug, name=b.name, categories=sorted({c.category for c in b.charts}))


@router.get("", response_model=list[BrandOut])
async def list_brands(session: AsyncSession = Depends(get_session)) -> list[BrandOut]:
    rows = (await session.execute(select(Brand).order_by(Brand.name))).scalars().all()
    return [_out(b) for b in rows]


@router.post("", response_model=BrandOut, status_code=201)
async def create_brand(body: BrandIn, session: AsyncSession = Depends(get_session)) -> BrandOut:
    """Register a brand and its size charts (B2B onboarding)."""
    if (await session.execute(select(Brand).where(Brand.slug == body.slug))).scalar_one_or_none():
        raise HTTPException(409, "Brand slug already exists")
    b = Brand(slug=body.slug, name=body.name)
    for c in body.charts:
        b.charts.append(
            SizeChart(
                category=c.category.value,
                gender=c.gender.value,
                fit_type=c.fit_type.value,
                entries=[e.model_dump(mode="json") for e in c.entries],
            )
        )
    session.add(b)
    await session.commit()
    return _out(b)
