"""App configuration (CORS origins, env)."""

import os

CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "")
DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_cors_origins() -> list[str]:
    if CORS_ORIGINS_STR.strip():
        origins = [o.strip() for o in CORS_ORIGINS_STR.split(",") if o.strip()]
        return origins + DEFAULT_ORIGINS

    frontend_url = os.getenv("FRONTEND_URL", "")
    origins = list(DEFAULT_ORIGINS)
    if frontend_url:
        origins.append(frontend_url)

    # Allow all Vercel preview/production domains for this project
    origins.append("https://frontend-pi-five-96.vercel.app")
    origins.append("https://*.vercel.app")
    return origins
