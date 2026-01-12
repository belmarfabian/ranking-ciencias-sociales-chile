"""
Script para construir el ranking desde una lista de IDs de Google Scholar.

Este es el método más confiable cuando Google Scholar bloquea el scraping automático.

Uso:
    python src/build_ranking.py --input data/seed/investigadores.csv
    python src/build_ranking.py --input data/seed/investigadores.csv --serpapi
    python src/build_ranking.py --input data/seed/investigadores.csv --method manual
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from metrics import MetricsCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / 'data' / 'raw'
DATA_OUTPUT = BASE_DIR / 'data' / 'output'


def load_ids_from_file(filepath: str) -> list:
    """
    Carga IDs de investigadores desde un archivo CSV.

    El archivo debe tener al menos una columna 'scholar_id'.
    """
    path = Path(filepath)

    if path.suffix == '.csv':
        df = pd.read_csv(path)
    elif path.suffix in ['.xlsx', '.xls']:
        df = pd.read_excel(path)
    else:
        # Texto plano, un ID por línea
        with open(path, 'r') as f:
            ids = [line.strip() for line in f if line.strip()]
        return ids

    # Buscar columna de ID
    for col in ['scholar_id', 'id', 'google_scholar_id', 'ID', 'ScholarID']:
        if col in df.columns:
            return df[col].dropna().astype(str).tolist()

    logger.error("No se encontró columna de ID en el archivo")
    return []


def fetch_with_serpapi(scholar_ids: list) -> list:
    """Obtiene datos usando SerpAPI."""
    from scraper_serpapi import SerpAPIScholarScraper

    api_key = os.environ.get('SERPAPI_KEY')
    if not api_key:
        logger.error("Se requiere SERPAPI_KEY en variables de entorno")
        print("\nConfigura tu API key:")
        print("  Windows: set SERPAPI_KEY=tu_api_key")
        print("  Linux/Mac: export SERPAPI_KEY=tu_api_key")
        return []

    scraper = SerpAPIScholarScraper(api_key=api_key)
    return scraper.get_authors_from_ids(scholar_ids)


def fetch_with_scholarly(scholar_ids: list) -> list:
    """Intenta obtener datos con scholarly."""
    from scraper import ScholarScraper

    scraper = ScholarScraper(use_proxy=True, delay_range=(5, 10))
    authors = []

    for scholar_id in scholar_ids:
        author = scraper.get_author_by_id(scholar_id)
        if author:
            authors.append(author)
        time.sleep(2)

    return authors


def manual_entry_mode(scholar_ids: list) -> list:
    """
    Modo de entrada manual.
    Abre cada perfil en el navegador y pide al usuario ingresar los datos.
    """
    import webbrowser

    authors = []
    print("\n" + "=" * 60)
    print("MODO DE ENTRADA MANUAL")
    print("=" * 60)
    print("Se abrirá cada perfil en el navegador.")
    print("Ingresa los datos que se solicitan.\n")

    for i, scholar_id in enumerate(scholar_ids):
        print(f"\n--- Investigador {i+1}/{len(scholar_ids)} ---")
        url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en"
        print(f"Abriendo: {url}")

        try:
            webbrowser.open(url)
        except:
            print(f"No se pudo abrir. Visita manualmente: {url}")

        time.sleep(1)

        print("\nIngresa los datos (o 'skip' para saltar, 'quit' para terminar):")

        name = input("  Nombre: ").strip()
        if name.lower() == 'quit':
            break
        if name.lower() == 'skip':
            continue

        affiliation = input("  Afiliación: ").strip()

        try:
            h_index = int(input("  H-index: ").strip() or 0)
            citations = int(input("  Citas totales: ").strip() or 0)
            i10_index = int(input("  i10-index: ").strip() or 0)
        except ValueError:
            h_index, citations, i10_index = 0, 0, 0

        interests = input("  Intereses (separados por coma): ").strip()
        interests_list = [i.strip() for i in interests.split(',')] if interests else []

        author = {
            'scholar_id': scholar_id,
            'name': name,
            'affiliation': affiliation,
            'email_domain': '',
            'interests': interests_list,
            'h_index': h_index,
            'h_index_5y': 0,
            'i10_index': i10_index,
            'i10_index_5y': 0,
            'citations': citations,
            'citations_5y': 0,
            'url_picture': '',
            'homepage': '',
            'cites_per_year': {},
            'extracted_at': datetime.now().isoformat()
        }

        authors.append(author)
        print(f"  Agregado: {name}")

    return authors


def save_results(authors: list, generate_ranking: bool = True):
    """Guarda los resultados."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Guardar datos crudos
    raw_file = DATA_RAW / f'authors_{timestamp}.json'
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(authors, f, ensure_ascii=False, indent=2)
    logger.info(f"Datos guardados en {raw_file}")

    if generate_ranking and authors:
        # Generar ranking
        calc = MetricsCalculator(authors)
        ranking = calc.generate_ranking()
        stats = calc.get_statistics()

        # CSV
        csv_file = DATA_OUTPUT / f'ranking_ciencias_sociales_{timestamp[:8]}.csv'
        ranking.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"CSV: {csv_file}")

        # Excel
        xlsx_file = DATA_OUTPUT / f'ranking_ciencias_sociales_{timestamp[:8]}.xlsx'
        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            ranking.to_excel(writer, sheet_name='Ranking', index=False)
        logger.info(f"Excel: {xlsx_file}")

        # Mostrar top 20
        print("\n" + "=" * 60)
        print("TOP 20 INVESTIGADORES")
        print("=" * 60)
        print(ranking[['rank', 'name', 'h_index', 'citations', 'affiliation']].head(20).to_string(index=False))

        return ranking

    return None


def main():
    parser = argparse.ArgumentParser(description='Construir ranking desde lista de IDs')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='Archivo con IDs de investigadores')
    parser.add_argument('--serpapi', action='store_true',
                       help='Usar SerpAPI para obtener datos')
    parser.add_argument('--scholarly', action='store_true',
                       help='Usar scholarly (puede ser bloqueado)')
    parser.add_argument('--manual', action='store_true',
                       help='Modo de entrada manual')
    parser.add_argument('--no-ranking', action='store_true',
                       help='Solo obtener datos, no generar ranking')

    args = parser.parse_args()

    # Cargar IDs
    scholar_ids = load_ids_from_file(args.input)
    if not scholar_ids:
        print("No se encontraron IDs en el archivo")
        return

    print(f"Cargados {len(scholar_ids)} IDs de investigadores")

    # Obtener datos
    authors = []

    if args.serpapi:
        print("\nUsando SerpAPI...")
        authors = fetch_with_serpapi(scholar_ids)

    elif args.scholarly:
        print("\nUsando scholarly (puede ser lento o fallar por bloqueos)...")
        authors = fetch_with_scholarly(scholar_ids)

    elif args.manual:
        authors = manual_entry_mode(scholar_ids)

    else:
        # Por defecto, intentar serpapi si hay key, sino manual
        if os.environ.get('SERPAPI_KEY'):
            print("\nSERPAPI_KEY encontrada, usando SerpAPI...")
            authors = fetch_with_serpapi(scholar_ids)
        else:
            print("\nNo hay SERPAPI_KEY. Opciones:")
            print("1. Configura SERPAPI_KEY (gratis en serpapi.com)")
            print("2. Usa --manual para entrada manual")
            print("3. Usa --scholarly (puede fallar por bloqueos)")
            return

    if not authors:
        print("No se obtuvieron datos de investigadores")
        return

    print(f"\nObtenidos datos de {len(authors)} investigadores")

    # Guardar
    save_results(authors, generate_ranking=not args.no_ranking)


if __name__ == "__main__":
    main()
