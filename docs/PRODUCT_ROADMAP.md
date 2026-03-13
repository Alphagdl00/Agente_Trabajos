# Product Roadmap

## Vision

Convertir `Job Radar` en un producto SaaS que entregue un feed diario de vacantes relevantes, directas y priorizadas para perfiles especializados.

La propuesta de valor no es "buscar vacantes".
La propuesta es:

- reducir ruido
- aumentar precision
- ahorrar tiempo
- ayudar a decidir que aplicar hoy

## Product Principles

- El usuario debe entender en menos de 30 segundos por que una vacante aparece.
- La experiencia principal debe ser "Top oportunidades para ti hoy", no una tabla.
- Los filtros de exploracion no deben disparar scraping.
- El scraping corre en background; el usuario solo ve resultados ya procesados.
- La personalizacion viene de perfil explicito + comportamiento del usuario.

## 30 Day Plan

### Week 1

Objetivo: cerrar la base de producto actual.

- estabilizar UX actual
- terminar filtros por practica, seniority, region y pais
- asegurar que la metadata de `country`, `region` y `seniority_level` se persista
- ampliar cobertura ATS faltante prioritaria
- definir eventos de usuario minimos: view, save, apply_today, reject

Entregable:

- una experiencia usable para piloto cerrado

### Week 2

Objetivo: separar producto de archivos locales.

- introducir esquema relacional inicial en Postgres
- definir repositorio de acceso a datos
- persistir jobs, companies, runs y acciones del usuario en DB
- conservar los exports Excel solo como output secundario

Entregable:

- primer backend con almacenamiento durable

### Week 3

Objetivo: mover ejecucion a background.

- extraer scraping a un servicio o modulo de jobs
- agregar cola de tareas
- programar corridas por perfil o por mercado
- guardar resultados por fecha de corrida
- cachear scraping por empresa

Entregable:

- corridas automaticas fuera de la sesion del usuario

### Week 4

Objetivo: preparar piloto de producto.

- agregar autenticacion
- crear perfil persistente del usuario
- mostrar home personalizada
- agregar notificaciones simples
- medir activacion y retencion basica

Entregable:

- piloto usable para 5-10 usuarios reales

## Metrics

### Activation

- usuario configura practica y seniority
- usuario corre su primer radar
- usuario abre al menos 3 vacantes

### Engagement

- usuarios que vuelven al dia siguiente
- vacantes abiertas por sesion
- vacantes guardadas o marcadas para aplicar

### Quality

- porcentaje de vacantes con explicacion no vacia
- porcentaje de vacantes con metadata de region/pais
- tiempo promedio por corrida

### Commercial

- usuarios que piden seguir usando el producto
- usuarios dispuestos a pagar
- tiempo ahorrado reportado por usuario

## Scope To Avoid Right Now

- billing
- recomendaciones LLM en toda la base
- microservicios
- dashboards B2B complejos
- integraciones enterprise

## Near-Term Product Backlog

- onboarding de 3 pasos
- home con shortlist diaria
- acciones rapidas por vacante
- explicaciones cortas y legibles
- exploracion simple con filtros persistentes
- cobertura LATAM/Mexico
- cache de scraping por empresa
