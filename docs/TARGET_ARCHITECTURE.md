# Target Architecture

## Goal

Separar el sistema en capas para que el scraping, el ranking y la experiencia del usuario no dependan de archivos locales ni de la sesion de Streamlit.

## Proposed Architecture

### Frontend

- web app para usuario final
- en el corto plazo, Streamlit puede seguir como consola operativa
- en el mediano plazo, migrar a un frontend web con login

### API Layer

- `FastAPI`
- endpoints para:
  - perfil de usuario
  - vacantes
  - shortlist diaria
  - filtros
  - acciones del usuario

### Background Jobs

- worker de scraping
- worker de enrichment/scoring
- scheduler para corridas automaticas

Opciones:

- `Celery + Redis`
- o una version mas simple con `RQ`

### Database

- `PostgreSQL`
- fuente de verdad para:
  - users
  - profiles
  - companies
  - jobs
  - job_runs
  - job_matches
  - user_job_actions

### Storage

- archivos de export opcionales
- snapshots de debug
- logs de scraping

## Data Flow

1. Un usuario define su perfil.
2. El scheduler lanza una corrida.
3. El worker scrapea empresas y ATS.
4. El sistema normaliza y deduplica vacantes.
5. El motor calcula score base.
6. El sistema genera matches por usuario usando practica, seniority, geografia y feedback.
7. El frontend muestra shortlist y exploracion.
8. El usuario guarda, aplica o descarta, y esas acciones retroalimentan el ranking.

## Separation Of Concerns

### Scraping

- sabe obtener vacantes
- no sabe de usuarios

### Normalization

- unifica campos entre ATS
- deduplica

### Ranking

- calcula relevancia
- explica razones

### Matching

- adapta ranking al perfil del usuario

### Presentation

- muestra solo la informacion necesaria
- no expone campos internos innecesarios

## Migration Strategy

### Phase 1

- mantener Streamlit
- introducir Postgres
- guardar corridas y resultados

### Phase 2

- mover scraping a jobs en background
- leer resultados desde API/DB

### Phase 3

- autenticacion
- panel por usuario

## Performance Strategy

- cache por empresa/ATS
- no re-scrapear empresas corridas hoy si no hay invalidador
- usar filtros de universo antes del scrape solo cuando el usuario quiera una corrida dirigida
- limitar top empresas en modo rapido
- guardar resultados normalizados para reutilizacion por varios usuarios
