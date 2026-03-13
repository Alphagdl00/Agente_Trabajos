from __future__ import annotations

from backend.core.db import create_all
from backend.models import application, company, job, resume, skill, user  # noqa: F401


def main() -> None:
    created = create_all()
    if not created:
        raise RuntimeError("DATABASE_URL no está configurado. No se pudo crear el esquema Phase 1.")
    print("North Hound Phase 1 schema created successfully.")


if __name__ == "__main__":
    main()
