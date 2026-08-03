"""`python -m api` — run the marsad web backend (127.0.0.1 only)."""
import os

import uvicorn


def main():
    port = int(os.environ.get("MARSAD_PORT", "8765"))
    uvicorn.run("api.app:app", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
