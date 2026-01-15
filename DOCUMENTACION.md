# Ranking Ciencias Sociales Chile - Documentación

## Resumen del Sistema

Sistema automatizado para generar un ranking de investigadores chilenos en ciencias sociales, usando datos de OpenAlex y Google Scholar.

**URL de la web:** https://belmarfabian.github.io/ranking-ciencias-sociales-chile/

## Estadísticas Actuales (2026-01-14)

- **16,295 investigadores** de ciencias sociales en Chile
- **143 con Google Scholar ID** verificado
- H-index máximo: 135
- ~4.9 millones de citas totales

## Estructura de Archivos

```
ranking-ciencias-sociales/
├── docs/
│   ├── index.html          # Página web principal
│   └── ranking_web.json    # Datos JSON para la web
├── src/
│   ├── extraer_openalex.py    # Extrae datos de API OpenAlex
│   ├── procesar_ranking.py    # Procesa y genera ranking
│   └── actualizar_ranking.py  # Script unificado
├── data/
│   ├── raw/                # Datos crudos de OpenAlex
│   ├── processed/          # Datos procesados
│   └── output/             # Archivos finales (CSV, JSON)
└── DOCUMENTACION.md        # Este archivo
```

## Cómo Actualizar el Ranking

### Opción 1: Actualización completa

```bash
# 1. Extraer datos frescos de OpenAlex (~4 minutos)
python src/extraer_openalex.py

# 2. Procesar y generar ranking
python src/procesar_ranking.py

# 3. Copiar a la web
cp data/output/ranking_web_FECHA.json docs/ranking_web.json

# 4. Subir cambios
git add docs/ranking_web.json
git commit -m "Actualizar ranking"
git push
```

### Opción 2: Solo reprocesar (sin descargar nuevos datos)

```bash
python src/procesar_ranking.py
cp data/output/ranking_web_*.json docs/ranking_web.json
git add . && git commit -m "Actualizar" && git push
```

## Scripts

### extraer_openalex.py

Conecta a la API de OpenAlex (gratuita, sin autenticación) y extrae:
- Autores con afiliación en instituciones chilenas
- Filtro: h-index > 1
- Campos: ciencias sociales (Sociology, Political Science, Economics, Psychology, Education, etc.)

**Salida:** `data/raw/investigadores_openalex_FECHA.csv`

### procesar_ranking.py

1. Carga datos de OpenAlex
2. Limpia errores (excluye no-chilenos, instituciones extranjeras)
3. Clasifica por disciplina
4. Agrega Google Scholar IDs conocidos
5. Genera CSV final y JSON para web

**Configuración importante:**
- `H_INDEX_MINIMO = 1` - Filtro de h-index mínimo
- `EXCLUIR_NOMBRES` - Lista de investigadores a excluir (errores de OpenAlex)
- `EXCLUIR_AFILIACIONES` - Instituciones no chilenas a excluir
- `SCHOLAR_IDS_CONOCIDOS` - Diccionario de Google Scholar IDs verificados

## Google Scholar IDs

Los Scholar IDs se agregan manualmente al diccionario `SCHOLAR_IDS_CONOCIDOS` en `procesar_ranking.py`.

Para agregar nuevos IDs:
1. Buscar el perfil en Google Scholar
2. Copiar el ID de la URL (ej: `scholar.google.com/citations?user=XXXXX`)
3. Agregar al diccionario: `"Nombre Completo": "XXXXX",`

**IDs agregados hasta ahora:** ~170 investigadores verificados

## API de OpenAlex

- **URL base:** https://api.openalex.org
- **Documentación:** https://docs.openalex.org
- **Límite:** 100,000 requests/día (sin autenticación)
- **Filtros usados:**
  - `last_known_institutions.country_code:cl` - Instituciones chilenas
  - `summary_stats.h_index:>1` - H-index mínimo

## Notas Importantes

### Juan Pablo Luna
No aparece en el ranking porque su afiliación principal en OpenAlex es McGill University (Canadá). Su Scholar ID es `IgwSc8oAAAAJ`.

### Campos incluidos
- Sociology, Political Science, Economics
- Psychology, Education, Law
- Business, Geography, Anthropology
- Communication, Social Work, Public Policy
- Y otros campos de ciencias sociales

### Problemas conocidos
- Algunos investigadores extranjeros aparecen por error de afiliación en OpenAlex
- El encoding de Windows causa errores al imprimir caracteres especiales (no afecta los archivos)

## Historial de Cambios

### 2026-01-14
- Implementado sistema de actualización automática con API OpenAlex
- Expandido de 1,089 a 16,295 investigadores
- Agregados 143 Google Scholar IDs verificados

### 2026-01-13
- Expandido h-index mínimo de 2 a 1
- Agregados filtros por disciplina e institución
- Implementado ranking institucional
- Agregada descarga CSV
