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

## API mínima Phase 1

Levantar API:

```bash
.\.venv\Scripts\uvicorn.exe backend.api.app:app --reload
```

Endpoints nuevos:

- `GET /health`
- `GET /profile`
- `POST /phase1/ingest`
- `GET /phase1/runs/latest`
- `GET /phase1/jobs`
- `GET /phase1/matches`
- `GET /runs/latest`
- `GET /jobs/latest`

Ejemplo para correr la ingesta nueva con el perfil activo:

```bash
curl -X POST http://127.0.0.1:8000/phase1/ingest
```

Después de ingerir, puedes revisar la capa nueva:

```bash
curl http://127.0.0.1:8000/phase1/jobs
curl http://127.0.0.1:8000/phase1/matches
curl http://127.0.0.1:8000/phase1/runs/latest
```

La ingesta nueva ahora también:
- persiste `skills_v2`
- vincula `job_skills_v2`
- vincula `user_skills_v2`
- recalcula `job_matches_v2` con explicación determinística
- registra `ingestion_runs_v2` para auditar cada corrida

En la app Streamlit:
- si SQLAlchemy está instalado y existen matches `v2`
- se mostrará una sección `North Hound Phase 1`
- la home priorizará `matches v2` para `Top 10`, `Apuestas fuertes` y `Explorar`
- el flujo actual sigue como fallback si la capa nueva no está disponible
