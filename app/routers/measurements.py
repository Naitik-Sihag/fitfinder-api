from fastapi import APIRouter, Depends

from app.schemas import EstimateRequest, EstimateResponse
from app.security import require_api_key
from app.services.estimator import Estimator, get_estimator

router = APIRouter(prefix="/v1/measurements", tags=["measurements"], dependencies=[Depends(require_api_key)])


@router.post("/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest, est: Estimator = Depends(get_estimator)) -> EstimateResponse:
    """Estimate chest/waist/hip/shoulder (cm) from height, weight and gender."""
    return est.estimate(req)
