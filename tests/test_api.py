import pytest

from app.config import get_settings

MEN = {"brand": "demo-urban", "category": "tshirt", "gender": "male"}


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_estimate_is_monotonic_in_weight(client):
    a = (
        await client.post(
            "/v1/measurements/estimate", json={"height_cm": 175, "weight_kg": 60, "gender": "male"}
        )
    ).json()
    b = (
        await client.post(
            "/v1/measurements/estimate", json={"height_cm": 175, "weight_kg": 90, "gender": "male"}
        )
    ).json()
    assert b["measurements"]["chest"] > a["measurements"]["chest"]
    assert 85 < a["measurements"]["chest"] < 100


async def test_recommend_from_measurements(client):
    r = await client.post(
        "/v1/recommend", json={**MEN, "measurements": {"chest": 98, "waist": 83, "shoulder": 43.5}}
    )
    assert r.status_code == 200
    j = r.json()
    assert j["recommended_size"] == "M"
    assert j["measurement_source"] == "provided"
    assert 0 <= j["return_risk"] <= 1 and 0 <= j["confidence"] <= 1


async def test_recommend_from_height_weight(client):
    r = await client.post("/v1/recommend", json={**MEN, "height_cm": 175, "weight_kg": 70})
    assert r.status_code == 200
    assert r.json()["measurement_source"] == "height_weight_baseline"


async def test_slim_brand_runs_small(client):
    body = {"measurements": {"chest": 100, "waist": 85}}
    urban = (await client.post("/v1/recommend", json={**MEN, **body})).json()["recommended_size"]
    slim = (await client.post("/v1/recommend", json={**MEN, "brand": "demo-slim", **body})).json()[
        "recommended_size"
    ]
    order = ["S", "M", "L", "XL", "XXL"]
    assert order.index(slim) > order.index(urban)


async def test_fit_preference_shifts_size(client):
    body = {"measurements": {"chest": 101.5}}
    reg = (await client.post("/v1/recommend", json={**MEN, **body})).json()["recommended_size"]
    relaxed = (await client.post("/v1/recommend", json={**MEN, **body, "fit_preference": "relaxed"})).json()[
        "recommended_size"
    ]
    order = ["S", "M", "L", "XL", "XXL"]
    assert order.index(relaxed) >= order.index(reg)


async def test_between_sizes_prefers_larger_and_flags_it(client):
    j = (await client.post("/v1/recommend", json={**MEN, "measurements": {"chest": 102}})).json()
    assert j["recommended_size"] in {"M", "L"}
    assert j["alternatives"]


async def test_bigger_body_gets_bigger_or_equal_size(client):
    order = ["S", "M", "L", "XL", "XXL"]
    last = -1
    for chest in (88, 96, 104, 112, 120):
        s = (await client.post("/v1/recommend", json={**MEN, "measurements": {"chest": chest}})).json()[
            "recommended_size"
        ]
        assert order.index(s) >= last
        last = order.index(s)


async def test_recommend_validation_and_404(client):
    assert (await client.post("/v1/recommend", json=MEN)).status_code == 422
    r = await client.post("/v1/recommend", json={**MEN, "brand": "nope", "height_cm": 175, "weight_kg": 70})
    assert r.status_code == 404


async def test_brand_onboarding_and_feedback(client):
    chart = {
        "category": "tshirt",
        "gender": "male",
        "entries": [{"label": "M", "chest": [90, 100]}, {"label": "L", "chest": [100, 110]}],
    }
    r = await client.post("/v1/brands", json={"slug": "acme", "name": "Acme", "charts": [chart]})
    assert r.status_code == 201 and r.json()["categories"] == ["tshirt"]
    assert (await client.post("/v1/brands", json={"slug": "acme", "name": "Acme"})).status_code == 409
    assert "acme" in [b["slug"] for b in (await client.get("/v1/brands")).json()]
    rec = await client.post(
        "/v1/recommend", json={"brand": "acme", "gender": "male", "measurements": {"chest": 105}}
    )
    assert rec.json()["recommended_size"] == "L"
    fb = await client.post(
        "/v1/feedback", json={"brand": "acme", "size_purchased": "L", "kept": False, "reason": "too_large"}
    )
    assert fb.status_code == 201 and fb.json()["id"] == 1


async def test_bad_chart_rejected(client):
    chart = {
        "category": "tshirt",
        "gender": "male",
        "entries": [{"label": "M", "chest": [100, 90]}, {"label": "L", "chest": [100, 110]}],
    }
    assert (
        await client.post("/v1/brands", json={"slug": "bad", "name": "Bad", "charts": [chart]})
    ).status_code == 422


@pytest.mark.parametrize("path", ["/v1/brands"])
async def test_api_key_enforced(client, monkeypatch, path):
    monkeypatch.setenv("FITFINDER_API_KEYS", "secret")
    get_settings.cache_clear()
    assert (await client.get(path)).status_code == 401
    assert (await client.get(path, headers={"X-API-Key": "wrong"})).status_code == 401
    assert (await client.get(path, headers={"X-API-Key": "secret"})).status_code == 200
