# North Hound Phase 1

Esta fase introduce la base de la arquitectura objetivo sin romper el prototipo actual.

## Qué incluye

- `backend/core/`: sesión SQLAlchemy y metadatos base
- `backend/models/`: modelo normalizado para compañías, jobs, perfiles, skills, resumes, matches y applications
- `backend/schemas/`: modelo canónico `CanonicalJob`
- `backend/services/`: normalización de jobs y matching determinístico/explicable
- `backend/repositories/`: persistencia ORM para compañías, jobs y matches
- `backend/pipelines/`: pipeline estándar `scrape -> normalize -> deduplicate -> persist -> recalculate matches`
- `backend/tasks/`: punto de entrada para scans programados
- `alembic/`: base para migraciones formales

## Orden recomendado

1. Instalar dependencias nuevas
2. Configurar `DATABASE_URL`
3. Crear esquema inicial
4. Ejecutar el pipeline de ingesta
5. Conectar endpoints del backend a esta nueva capa

## Comandos

```bash
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe backend\bootstrap_phase1.py
```

Cuando `alembic` ya esté activo:

```bash
.\.venv\Scripts\alembic.exe revision --autogenerate -m "phase1 baseline"
.\.venv\Scripts\alembic.exe upgrade head
```
