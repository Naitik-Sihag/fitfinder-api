from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__, db
from app.config import get_settings
from app.routers import brands, feedback, health, measurements, sizes
from app.services.seed import seed_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db.init_engine()
    await db.create_tables()
    if settings.seed_demo_data:
        async with db._sessionmaker() as s:  # noqa: SLF001
            await seed_demo(s)
    yield
    await db.dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FitFinder API",
        version=__version__,
        description="AI size & fit recommendations for online clothing. Fewer wrong sizes, fewer returns.",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
    for r in (health.router, measurements.router, sizes.router, brands.router, feedback.router):
        app.include_router(r)
    return app


app = create_app()
