# Capturas necesarias para GitHub y portfolio

Este documento define las capturas que faltan para presentar Nexus Predictor de forma profesional.

## Carpeta recomendada

```text
docs/assets/screenshots/
```

## Capturas prioritarias

### 1. Home / dashboard principal

Archivo sugerido:

```text
docs/assets/screenshots/01-dashboard-overview.png
```

Debe mostrar:

- título del producto;
- métricas principales;
- estado de edición/año;
- estética visual general.

### 2. Mapa de Fabrik

```text
docs/assets/screenshots/02-fabrik-map.png
```

Debe mostrar:

- salas;
- presión/saturación;
- visualización diferenciada.

### 3. Ranking de artistas / demanda

```text
docs/assets/screenshots/03-artist-demand-ranking.png
```

Debe mostrar:

- artistas principales;
- demand score;
- explicación o factores.

### 4. Timetable probable

```text
docs/assets/screenshots/04-probable-timetable.png
```

Debe mostrar:

- horarios;
- salas;
- artistas;
- aviso de que no es horario oficial.

### 5. Variantes optimizadas

```text
docs/assets/screenshots/05-optimized-variants.png
```

Debe mostrar:

- anti-crowding;
- balanced;
- fan experience.

### 6. Perfil de artista

```text
docs/assets/screenshots/06-artist-profile.png
```

Debe mostrar:

- datos del artista;
- género;
- señales externas;
- explicación de demanda.

### 7. Admin / data review

```text
docs/assets/screenshots/07-admin-data-review.png
```

Debe mostrar:

- revisión de datos;
- estado de fuentes;
- enfoque ML-ready.

## Buenas prácticas

- Usar datos demo, no secretos ni tokens.
- Evitar capturas con errores de consola.
- Usar resolución 1440px o superior para capturas desktop.
- Añadir una o dos capturas mobile si la UI está bien adaptada.
- Mantener nombres de archivo estables para que el README no se rompa.

## Cómo integrarlas después en README

Cuando existan las capturas, añadir una sección así:

```markdown
## Capturas

![Dashboard overview](docs/assets/screenshots/01-dashboard-overview.png)
![Fabrik map](docs/assets/screenshots/02-fabrik-map.png)
![Probable timetable](docs/assets/screenshots/04-probable-timetable.png)
```
