from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Feedback
from app.schemas import FeedbackIn, FeedbackOut
from app.security import require_api_key

router = APIRouter(prefix="/v1/feedback", tags=["feedback"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(body: FeedbackIn, session: AsyncSession = Depends(get_session)) -> Feedback:
    """Record whether a purchase was kept or returned. This is the training data for the ML model."""
    row = Feedback(
        user_ref=body.user_ref,
        brand_slug=body.brand,
        category=body.category.value,
        size_purchased=body.size_purchased,
        size_recommended=body.size_recommended,
        kept=body.kept,
        reason=body.reason,
        measurements=body.measurements.model_dump() if body.measurements else None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
