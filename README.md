# Ranking Chileno de Ciencias Sociales

Ranking de impacto académico de científicos sociales en Chile basado en métricas de Google Scholar.

## Inicio Rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Opción A: Usar SerpAPI (recomendado - 100 búsquedas gratis/mes)
#    Crear cuenta en https://serpapi.com y obtener API key
set SERPAPI_KEY=tu_api_key                                          # Windows
export SERPAPI_KEY=tu_api_key                                        # Linux/Mac
python src/build_ranking.py --input data/seed/investigadores_chile.csv --serpapi

# 3. Opción B: Entrada manual (abre cada perfil en navegador)
python src/build_ranking.py --input data/seed/investigadores_chile.csv --manual
```

## Metodología

Inspirado en el [CPS-Ranking](https://github.com/bgonzalezbustamante/CPS-Ranking) de Bastián González-Bustamante.

### Disciplinas incluidas

- Sociología
- Ciencia Política
- Economía
- Antropología
- Psicología
- Trabajo Social
- Historia
- Geografía
- Comunicación Social
- Educación
- Demografía
- Administración Pública
- Relaciones Internacionales
- Estudios Urbanos
- Estudios de Género
- Otras ciencias sociales

### Criterios de inclusión

1. **Afiliación**: Investigadores con afiliación a instituciones chilenas
2. **Perfil activo**: Cuenta activa en Google Scholar
3. **Disciplina**: Auto-identificación en campos de ciencias sociales

### Métricas

| Métrica | Descripción |
|---------|-------------|
| H-Index | Índice principal de ordenamiento |
| Citas totales | Número total de citaciones |
| i10-Index | Publicaciones con 10+ citas |
| Citas últimos 5 años | Impacto reciente |
| C-Index | Índice de consistencia del perfil (0-100) |
| Impact Score | Score compuesto de impacto |

## Estructura del proyecto

```
├── data/
│   ├── raw/                 # Datos crudos extraídos
│   ├── processed/           # Datos procesados
│   ├── output/              # Rankings generados (CSV, Excel)
│   └── seed/                # Lista semilla de investigadores
├── src/
│   ├── main.py              # Script principal (scraping automático)
│   ├── build_ranking.py     # Construir desde lista de IDs
│   ├── scraper.py           # Scraper con scholarly
│   ├── scraper_alt.py       # Scraper alternativo (requests)
│   ├── scraper_serpapi.py   # Scraper con SerpAPI
│   ├── metrics.py           # Cálculo de métricas
│   ├── add_researchers.py   # Agregar investigadores
│   └── test_scraper.py      # Tests
├── config/
│   └── config.yaml          # Configuración (universidades, disciplinas)
└── requirements.txt
```

## Uso detallado

### Construir ranking desde lista de IDs (recomendado)

```bash
# Con SerpAPI (más confiable)
python src/build_ranking.py --input data/seed/investigadores_chile.csv --serpapi

# Entrada manual (sin API)
python src/build_ranking.py --input data/seed/investigadores_chile.csv --manual

# Con scholarly (puede fallar por bloqueos)
python src/build_ranking.py --input data/seed/investigadores_chile.csv --scholarly
```

### Agregar investigadores individualmente

```bash
# Por ID de Google Scholar
python src/add_researchers.py --id ABC123XYZ

# Buscar por nombre
python src/add_researchers.py --search "Nombre Apellido universidad"
```

### Scraping automático completo

```bash
# Modo test (pocos resultados)
python src/main.py --test

# Ejecución completa (puede tomar tiempo y ser bloqueado)
python src/main.py
```

## Cómo encontrar el ID de Google Scholar

1. Ve al perfil del investigador en Google Scholar
2. La URL tiene formato: `scholar.google.com/citations?user=XXXXXXXXX`
3. El ID es la parte después de `user=` (ej: `UknWOrEAAAAJ`)

## Agregar investigadores a la lista semilla

Edita `data/seed/investigadores_chile.csv` y agrega filas:

```csv
scholar_id,nombre_referencia,disciplina,institucion_referencia
NUEVO_ID,Nombre del Investigador,Disciplina,Universidad
```

## Nota sobre bloqueos

Google Scholar puede bloquear peticiones automatizadas. Opciones:

1. **SerpAPI** (recomendado): 100 búsquedas gratis/mes en serpapi.com
2. **Entrada manual**: El script abre cada perfil en el navegador
3. **Esperar**: Los bloqueos suelen ser temporales (minutos a horas)

## Output

El sistema genera en `data/output/`:
- `ranking_ciencias_sociales_YYYYMMDD.csv` - Ranking en CSV
- `ranking_ciencias_sociales_YYYYMMDD.xlsx` - Ranking en Excel con estadísticas

## Licencia

MIT License para código, CC-BY-4.0 para datos.
