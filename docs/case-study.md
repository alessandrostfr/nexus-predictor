# Case study — Nexus Predictor

## Resumen

Nexus Predictor es una plataforma full stack para analizar el festival Nexus en Fabrik Madrid y simular demanda, saturación por sala y horarios probables a partir de datos históricos, perfiles de artistas y señales externas.

El objetivo no es adivinar un horario oficial, sino construir un sistema técnico capaz de:

- estructurar datos complejos;
- evaluar popularidad/demanda de artistas;
- simular presión por salas y franjas horarias;
- preparar una base ML-ready trazable;
- visualizar resultados de forma útil para el usuario.

## Problema

Un festival con varias salas y muchos artistas puede generar saturaciones, solapamientos y decisiones complejas de movilidad. La pregunta de producto es:

> Si conocemos el histórico del festival, la capacidad de las salas y señales de demanda de cada artista, ¿podemos estimar qué zonas y franjas tendrán más presión?

## Solución

El proyecto se construye como una plataforma con tres capas:

1. **Backend de datos y APIs**  
   FastAPI, PostgreSQL, Alembic, SQLAlchemy, endpoints versionados y scripts de validación.

2. **Capa predictiva / ML-ready**  
   Evidencia, snapshots, métricas normalizadas, features, labels/proxies, model runs y predicciones persistibles.

3. **Frontend de visualización**  
   Next.js + TypeScript con dashboard, mapa, rankings, timetable, salas y explicaciones.

## Decisiones técnicas importantes

### PostgreSQL + Alembic

El proyecto empezó con datos JSON/SQLite y evolucionó hacia PostgreSQL para soportar datos versionados, migraciones y despliegue profesional.

### Evidencia antes que predicción

La V3 introduce una regla estricta: antes de entrenar modelos, cada dato debe ser trazable. Por eso existen capas de raw snapshots, normalized metrics, feature snapshots, labels, model runs y predictions.

### Separación entre heurística, optimización y ML

El sistema evita llamar “ML” a reglas manuales o scoring. Las heurísticas sirven como baseline, pero el objetivo V3 es entrenar modelos reales con métricas de validación.

### Frontend con identidad visual propia

La interfaz evita parecer un dashboard genérico. Se diseñó con estética cyberpunk/Fabrik-night para que el proyecto sea recordable en portfolio.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Prefect
- pandas / numpy
- scikit-learn
- OR-Tools
- Next.js
- TypeScript
- Recharts
- Framer Motion
- Docker

## Funcionalidades destacables

- Dataset histórico Nexus 2022-2026.
- Perfilado de artistas.
- Clasificación por géneros.
- Integración con APIs musicales.
- Modelo de salas de Fabrik.
- Timetable histórico 2022-2025.
- Timetable probable 2026 no oficial.
- Variantes optimizadas de horario.
- Mapa y dashboard interactivo.
- Auditoría V3 para convertir el proyecto en ML-first.

## Qué aprendí / qué demuestra

- Diseñar un producto técnico a partir de un problema real.
- Evolucionar un MVP hacia una arquitectura más seria.
- Modelar datos relacionales con migraciones.
- Crear APIs limpias y testeables.
- Separar capas de datos, negocio, predicción y visualización.
- Documentar limitaciones y no vender como ML algo que aún es baseline.
- Construir frontend con narrativa visual y experiencia de producto.

## Limitaciones actuales

- Las predicciones actuales no son horarios oficiales.
- La V3 sigue en construcción; todavía se está completando la ingesta externa y la preparación de datos ML-ready.
- Algunas fuentes externas requieren credenciales, límites de uso o revisión manual.
- Los modelos finales de ML deben validarse con métricas antes de presentarse como predicción real.

## Próximos pasos

- Completar ingesta externa V3.4.
- Preparar SoundCloud-first artist intelligence.
- Construir datasets de entrenamiento.
- Entrenar modelos reales para demanda, placement y saturación.
- Mostrar métricas de validación en frontend.
- Desplegar demo pública en VPS.
