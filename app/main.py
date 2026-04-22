import logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1.router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(title="Personal Docs API", version="0.1.0")

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    # BearerAuth securityScheme 등록
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    # /health 제외한 모든 엔드포인트에 security 적용
    for path, path_item in openapi_schema.get("paths", {}).items():
        if path == "/health":
            continue
        for method in path_item.values():
            if isinstance(method, dict):
                method.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
