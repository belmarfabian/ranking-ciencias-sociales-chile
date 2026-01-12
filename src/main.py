"""
Script principal para generar el Ranking Chileno de Ciencias Sociales.

Uso:
    python src/main.py                    # Ejecución completa
    python src/main.py --test             # Modo test (pocos resultados)
    python src/main.py --from-file data/raw/authors.json  # Desde archivo existente
"""

import argparse
import json
import yaml
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

from scraper import ScholarScraper
from metrics import MetricsCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rutas
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / 'config' / 'config.yaml'
DATA_RAW = BASE_DIR / 'data' / 'raw'
DATA_OUTPUT = BASE_DIR / 'data' / 'output'


def load_config() -> dict:
    """Carga configuración desde YAML."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_scraping(config: dict, test_mode: bool = False) -> list:
    """
    Ejecuta el scraping de Google Scholar.

    Args:
        config: Configuración del proyecto
        test_mode: Si ejecutar en modo test (menos resultados)

    Returns:
        Lista de autores encontrados
    """
    logger.info("Iniciando scraping de Google Scholar...")

    scraper = ScholarScraper(
        use_proxy=False,
        delay_range=(
            config['scraping']['delay_min'],
            config['scraping']['delay_max']
        )
    )

    max_results = 5 if test_mode else 50

    # Obtener listas de búsqueda
    disciplines = config['disciplinas']
    universities = config['universidades']

    if test_mode:
        disciplines = disciplines[:3]
        universities = universities[:3]

    # Ejecutar búsqueda comprehensiva
    authors = scraper.search_comprehensive(
        disciplines=disciplines,
        universities=universities,
        max_per_search=max_results
    )

    # Guardar datos crudos
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_file = DATA_RAW / f'authors_{timestamp}.json'

    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(authors, f, ensure_ascii=False, indent=2)

    logger.info(f"Datos guardados en {raw_file}")

    return authors


def generate_ranking(authors: list, config: dict) -> pd.DataFrame:
    """
    Genera el ranking a partir de los datos de autores.

    Args:
        authors: Lista de autores
        config: Configuración

    Returns:
        DataFrame con el ranking
    """
    logger.info(f"Generando ranking con {len(authors)} autores...")

    calculator = MetricsCalculator(authors)
    ranking = calculator.generate_ranking(sort_by='h_index')

    # Estadísticas
    stats = calculator.get_statistics()
    logger.info(f"Estadísticas: {stats['total_authors']} autores, "
               f"H-index promedio: {stats['h_index']['mean']}")

    return ranking, stats


def save_outputs(ranking: pd.DataFrame, stats: dict, config: dict):
    """
    Guarda los resultados en múltiples formatos.

    Args:
        ranking: DataFrame con ranking
        stats: Estadísticas
        config: Configuración
    """
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d')
    base_name = config['output']['ranking_file']

    # CSV
    csv_path = DATA_OUTPUT / f'{base_name}_{timestamp}.csv'
    ranking.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"CSV guardado: {csv_path}")

    # Excel
    xlsx_path = DATA_OUTPUT / f'{base_name}_{timestamp}.xlsx'
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        ranking.to_excel(writer, sheet_name='Ranking', index=False)

        # Hoja de estadísticas
        stats_df = pd.DataFrame([
            {'Métrica': 'Total autores', 'Valor': stats['total_authors']},
            {'Métrica': 'H-index promedio', 'Valor': stats['h_index']['mean']},
            {'Métrica': 'H-index mediana', 'Valor': stats['h_index']['median']},
            {'Métrica': 'H-index máximo', 'Valor': stats['h_index']['max']},
            {'Métrica': 'Citas totales', 'Valor': stats['citations']['total']},
            {'Métrica': 'Citas promedio', 'Valor': stats['citations']['mean']},
            {'Métrica': 'Fecha generación', 'Valor': stats['generated_at']},
        ])
        stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

        # Top afiliaciones
        affil_df = pd.DataFrame([
            {'Institución': k, 'Cantidad': v}
            for k, v in stats['affiliations'].items()
        ])
        affil_df.to_excel(writer, sheet_name='Por Institución', index=False)

    logger.info(f"Excel guardado: {xlsx_path}")

    # JSON
    json_path = DATA_OUTPUT / f'{base_name}_{timestamp}.json'
    output_data = {
        'metadata': {
            'generated_at': stats['generated_at'],
            'total_authors': stats['total_authors'],
            'methodology': 'Google Scholar scraping',
            'version': '1.0'
        },
        'statistics': stats,
        'ranking': ranking.to_dict(orient='records')
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON guardado: {json_path}")

    # Ranking resumido para visualización rápida
    summary_path = DATA_OUTPUT / f'{base_name}_{timestamp}_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("RANKING CHILENO DE CIENCIAS SOCIALES\n")
        f.write(f"Generado: {timestamp}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Total de investigadores: {len(ranking)}\n")
        f.write(f"H-index promedio: {stats['h_index']['mean']}\n")
        f.write(f"H-index máximo: {stats['h_index']['max']}\n\n")

        f.write("-" * 70 + "\n")
        f.write("TOP 50 INVESTIGADORES\n")
        f.write("-" * 70 + "\n\n")

        for _, row in ranking.head(50).iterrows():
            f.write(f"{row['rank']:3}. {row['name'][:40]:<40} H:{row['h_index']:3} "
                   f"Citas:{row['citations']:6}\n")
            f.write(f"     {str(row['affiliation'])[:65]}\n\n")

    logger.info(f"Resumen guardado: {summary_path}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Ranking Chileno de Ciencias Sociales')
    parser.add_argument('--test', action='store_true', help='Modo test (pocos resultados)')
    parser.add_argument('--from-file', type=str, help='Cargar datos desde archivo JSON existente')
    parser.add_argument('--no-scrape', action='store_true', help='Solo generar ranking desde último archivo')

    args = parser.parse_args()

    # Cargar configuración
    config = load_config()

    # Obtener datos
    if args.from_file:
        logger.info(f"Cargando datos desde {args.from_file}")
        with open(args.from_file, 'r', encoding='utf-8') as f:
            authors = json.load(f)
    elif args.no_scrape:
        # Buscar último archivo
        raw_files = sorted(DATA_RAW.glob('authors_*.json'))
        if not raw_files:
            logger.error("No hay archivos de datos. Ejecute sin --no-scrape primero.")
            return
        latest = raw_files[-1]
        logger.info(f"Usando último archivo: {latest}")
        with open(latest, 'r', encoding='utf-8') as f:
            authors = json.load(f)
    else:
        authors = run_scraping(config, test_mode=args.test)

    if not authors:
        logger.error("No se encontraron autores.")
        return

    # Generar ranking
    ranking, stats = generate_ranking(authors, config)

    # Guardar resultados
    save_outputs(ranking, stats, config)

    logger.info("Proceso completado exitosamente!")
    print(f"\n{'='*50}")
    print(f"RANKING GENERADO: {len(ranking)} investigadores")
    print(f"{'='*50}")
    print(ranking[['rank', 'name', 'h_index', 'citations']].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
