from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Brand
from app.schemas import ChartEntry, EstimateRequest, RecommendRequest, RecommendResponse
from app.security import require_api_key
from app.services.estimator import Estimator, get_estimator
from app.services.recommender import recommend

router = APIRouter(prefix="/v1", tags=["recommendation"], dependencies=[Depends(require_api_key)])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_size(
    req: RecommendRequest,
    session: AsyncSession = Depends(get_session),
    est: Estimator = Depends(get_estimator),
) -> RecommendResponse:
    """Recommend the best size for a brand + garment, with confidence and return-risk."""
    brand = (await session.execute(select(Brand).where(Brand.slug == req.brand))).scalar_one_or_none()
    if brand is None:
        raise HTTPException(404, f"Unknown brand '{req.brand}'")
    chart = next(
        (c for c in brand.charts if c.category == req.category.value and c.gender == req.gender.value),
        None,
    )
    if chart is None:
        raise HTTPException(404, f"No {req.category.value}/{req.gender.value} chart for '{req.brand}'")

    if req.measurements is not None:
        body, source, unc = req.measurements, "provided", 1.0
    else:
        e = est.estimate(
            EstimateRequest(height_cm=req.height_cm, weight_kg=req.weight_kg, gender=req.gender, age=req.age)
        )
        body, source, unc = e.measurements, e.source, e.uncertainty_cm

    entries = [ChartEntry.model_validate(x) for x in chart.entries]
    return recommend(entries, body, req.fit_preference, source=source, uncertainty_cm=unc)
