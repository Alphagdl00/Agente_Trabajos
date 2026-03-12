# 🎯 Job Radar — Escanea 40+ Career Pages en Segundos

Herramienta open source que escanea directamente las career pages de empresas globales, puntúa vacantes contra tu perfil, y te muestra las más relevantes primero.

**No depende de LinkedIn, Indeed ni ningún intermediario.** Va directo a la fuente.

## 🚀 Demo en vivo

👉 **[Abrir Job Radar](https://agente-trabajos.streamlit.app)** *(próximamente)*

## ¿Cómo funciona?

1. **Elige un perfil** — Finance, Legal, Strategy, Operations, IT/Data, o escribe tus propias keywords
2. **Click en Escanear** — El radar revisa las APIs de career pages de 40+ empresas
3. **Revisa resultados** — Ordenados por score de relevancia, con links directos para aplicar

## ATS soportados

| ATS | Cobertura | Notas |
|-----|-----------|-------|
| **Greenhouse** | ✅ Completa | API pública, incluye descriptions |
| **Lever** | ✅ Completa | API pública, incluye descriptions |
| **Workday** | ✅ Completa | API interna, paginación automática |
| **SuccessFactors** | ⚠️ Parcial | Placeholder — en desarrollo |
| **Otros** | ⚠️ Genérico | Scraping HTML básico |

## Empresas incluidas

45 empresas globales preconfiguradas incluyendo J&J, Roche, Pfizer, Siemens, Microsoft, Stripe, y más. También puedes **subir tu propio CSV** con las empresas que quieras monitorear.

## Correr localmente

```bash
git clone https://github.com/Alphagdl00/Agente_Trabajos.git
cd Agente_Trabajos
pip install -r requirements.txt
streamlit run app.py
```

## Correr desde CLI (sin UI)

```bash
python main.py
```

Genera archivos Excel en `output/` con todas las vacantes escaneadas y filtradas.

## Estructura

```
├── app.py                  # Streamlit UI (multi-user)
├── main.py                 # Core engine: scraping, scoring, filtering
├── config/
│   ├── companies.csv       # Lista de empresas + career URLs
│   └── titles.txt          # Keywords default
├── src/
│   ├── ats_detector.py     # Auto-detecta qué ATS usa cada empresa
│   ├── ats_router.py       # Enruta al scraper correcto
│   ├── ats_greenhouse.py   # Scraper Greenhouse API
│   ├── ats_lever.py        # Scraper Lever API
│   ├── ats_workday.py      # Scraper Workday API
│   ├── ats_successfactors.py
│   └── ats_generic.py      # Fallback HTML scraper
├── .streamlit/config.toml  # Theme + deploy config
└── requirements.txt
```

## Personalizar empresas

Crea un CSV con estas columnas (solo `company` y `career_url` son obligatorias):

```csv
company,career_url,ats,industry,priority
Mi Empresa,https://boards.greenhouse.io/miempresa,greenhouse,Tech,A
Otra Corp,https://otra.wd3.myworkdayjobs.com/Careers,workday,Industrial,B
```

Súbelo desde la barra lateral de la app.

## Contribuir

PRs bienvenidos. Prioridades actuales:
- [ ] Más scrapers de ATS (iCIMS, SmartRecruiters, Taleo)
- [ ] GitHub Actions para scraping automático diario
- [ ] Notificaciones por email/Telegram de nuevas vacantes
- [ ] Mejor scoring con NLP/embeddings

## Licencia

MIT
