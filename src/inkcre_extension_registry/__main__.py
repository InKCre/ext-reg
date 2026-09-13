"""The single HTTP process used locally and by the container platform."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "inkcre_extension_registry.service.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        proxy_headers=True,
    )
