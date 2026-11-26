"""Body-measurement estimation.

`BaselineEstimator` is a transparent anthropometric heuristic (height, weight -> BMI -> girths).
It exists so the API works end-to-end today. It is meant to be replaced by a trained model
(see README "Training roadmap") behind the same `Estimator` protocol.
"""

from typing import Protocol

from app.schemas import BodyMeasurements, EstimateRequest, EstimateResponse, Gender


class Estimator(Protocol):
    version: str

    def estimate(self, req: EstimateRequest) -> EstimateResponse: ...


class BaselineEstimator:
    version = "baseline-anthro-0.1"

    # (intercept, per-BMI-point slope) in cm, hand-fitted to typical adult ranges.
    _COEF = {
        Gender.male: {"chest": (62.0, 1.55), "waist": (42.0, 1.80), "hip": (60.0, 1.60)},
        Gender.female: {"chest": (52.0, 1.60), "waist": (36.0, 1.75), "hip": (62.0, 1.50)},
    }
    _SHOULDER_RATIO = {Gender.male: 0.259, Gender.female: 0.238}

    def estimate(self, req: EstimateRequest) -> EstimateResponse:
        bmi = req.weight_kg / (req.height_cm / 100) ** 2
        c = self._COEF[req.gender]
        # Mild height correction around a 170cm reference: taller people have larger girths.
        h_adj = (req.height_cm - 170) * 0.10
        m = BodyMeasurements(
            chest=round(c["chest"][0] + c["chest"][1] * bmi + h_adj, 1),
            waist=round(c["waist"][0] + c["waist"][1] * bmi + h_adj, 1),
            hip=round(c["hip"][0] + c["hip"][1] * bmi + h_adj, 1),
            shoulder=round(self._SHOULDER_RATIO[req.gender] * req.height_cm, 1),
        )
        return EstimateResponse(
            measurements=m,
            uncertainty_cm=5.0,
            source="height_weight_baseline",
            model_version=self.version,
        )


def get_estimator() -> Estimator:
    return BaselineEstimator()
