from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Gender(StrEnum):
    male = "male"
    female = "female"


class Category(StrEnum):
    tshirt = "tshirt"
    shirt = "shirt"


class FitPreference(StrEnum):
    slim = "slim"
    regular = "regular"
    relaxed = "relaxed"


Cm = Annotated[float, Field(gt=20, lt=250)]


class BodyMeasurements(BaseModel):
    """Body measurements in centimetres. Only chest is mandatory."""

    chest: Annotated[float, Field(gt=60, lt=200)]
    waist: Annotated[float, Field(gt=40, lt=200)] | None = None
    hip: Annotated[float, Field(gt=50, lt=200)] | None = None
    shoulder: Annotated[float, Field(gt=25, lt=75)] | None = None


class EstimateRequest(BaseModel):
    height_cm: Annotated[float, Field(gt=100, lt=230)]
    weight_kg: Annotated[float, Field(gt=25, lt=250)]
    gender: Gender
    age: Annotated[int, Field(ge=13, le=100)] | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"height_cm": 175, "weight_kg": 70, "gender": "male"}}
    )


class EstimateResponse(BaseModel):
    measurements: BodyMeasurements
    uncertainty_cm: float = Field(description="Typical +/- error of the estimate, in cm")
    source: str
    model_version: str


class RecommendRequest(BaseModel):
    brand: str = Field(description="Brand slug, e.g. 'demo-urban'")
    category: Category = Category.tshirt
    gender: Gender
    fit_preference: FitPreference = FitPreference.regular
    # Provide either exact measurements (e.g. from a body scan) or height+weight to estimate.
    measurements: BodyMeasurements | None = None
    height_cm: Annotated[float, Field(gt=100, lt=230)] | None = None
    weight_kg: Annotated[float, Field(gt=25, lt=250)] | None = None
    age: Annotated[int, Field(ge=13, le=100)] | None = None

    @model_validator(mode="after")
    def _need_input(self) -> "RecommendRequest":
        if self.measurements is None and (self.height_cm is None or self.weight_kg is None):
            raise ValueError("Provide `measurements`, or both `height_cm` and `weight_kg`.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "brand": "demo-urban",
                "category": "tshirt",
                "gender": "male",
                "fit_preference": "regular",
                "height_cm": 175,
                "weight_kg": 70,
            }
        }
    )


class FitNote(BaseModel):
    measurement: str
    body_cm: float
    size_range_cm: tuple[float, float]
    verdict: str = Field(description="'good', 'snug' or 'loose'")


class SizeScore(BaseModel):
    size: str
    penalty: float
    return_risk: float


class RecommendResponse(BaseModel):
    recommended_size: str
    confidence: float = Field(ge=0, le=1)
    return_risk: float = Field(ge=0, le=1, description="Estimated chance of a size-related return")
    fit_notes: list[FitNote]
    alternatives: list[SizeScore]
    measurements_used: BodyMeasurements
    measurement_source: str
    model_version: str
    advice: str


class ChartEntry(BaseModel):
    label: str
    chest: tuple[float, float]
    waist: tuple[float, float] | None = None
    hip: tuple[float, float] | None = None
    shoulder: tuple[float, float] | None = None

    @model_validator(mode="after")
    def _ranges_ok(self) -> "ChartEntry":
        for name in ("chest", "waist", "hip", "shoulder"):
            r = getattr(self, name)
            if r is not None and r[0] > r[1]:
                raise ValueError(f"{name}: min must be <= max")
        return self


class ChartIn(BaseModel):
    category: Category
    gender: Gender
    fit_type: FitPreference = FitPreference.regular
    entries: Annotated[list[ChartEntry], Field(min_length=2)]


class BrandIn(BaseModel):
    slug: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}$")]
    name: Annotated[str, Field(min_length=1, max_length=120)]
    charts: list[ChartIn] = []


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    categories: list[str]


class FeedbackIn(BaseModel):
    user_ref: Annotated[str, Field(max_length=80)] | None = Field(
        default=None, description="Opaque pseudonymous id - never send names or emails"
    )
    brand: str
    category: Category = Category.tshirt
    size_purchased: Annotated[str, Field(max_length=10)]
    size_recommended: Annotated[str, Field(max_length=10)] | None = None
    kept: bool
    reason: str | None = Field(default=None, pattern=r"^(too_small|too_large|other)$")
    measurements: BodyMeasurements | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
