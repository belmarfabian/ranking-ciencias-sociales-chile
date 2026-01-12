"""
Script para agregar investigadores al ranking de forma manual.

Permite:
1. Agregar por ID de Google Scholar
2. Agregar desde un archivo CSV/Excel con IDs
3. Buscar y agregar por nombre

Uso:
    python src/add_researchers.py --id UknWOrEAAAAJ
    python src/add_researchers.py --file lista_ids.csv
    python src/add_researchers.py --search "Juan Pérez Universidad de Chile"
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from scraper import ScholarScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / 'data' / 'raw'


def load_existing_authors() -> dict:
    """Carga autores existentes del último archivo."""
    raw_files = sorted(DATA_RAW.glob('authors_*.json'))
    if raw_files:
        with open(raw_files[-1], 'r', encoding='utf-8') as f:
            authors = json.load(f)
            return {a['scholar_id']: a for a in authors}
    return {}


def save_authors(authors: dict):
    """Guarda la lista actualizada de autores."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = DATA_RAW / f'authors_{timestamp}.json'

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(list(authors.values()), f, ensure_ascii=False, indent=2)

    logger.info(f"Guardados {len(authors)} autores en {filepath}")


def add_by_id(scholar_id: str, authors: dict, scraper: ScholarScraper) -> bool:
    """Agrega un investigador por su ID de Scholar."""
    if scholar_id in authors:
        logger.info(f"ID {scholar_id} ya existe en el dataset")
        return False

    author = scraper.get_author_by_id(scholar_id)
    if author:
        authors[scholar_id] = author
        logger.info(f"Agregado: {author['name']}")
        return True
    else:
        logger.warning(f"No se pudo obtener datos para ID: {scholar_id}")
        return False


def add_from_file(filepath: str, authors: dict, scraper: ScholarScraper) -> int:
    """
    Agrega investigadores desde un archivo.

    El archivo debe tener una columna 'scholar_id' o 'id'.
    """
    path = Path(filepath)
    added = 0

    if path.suffix == '.csv':
        df = pd.read_csv(path)
    elif path.suffix in ['.xlsx', '.xls']:
        df = pd.read_excel(path)
    else:
        # Asumir texto plano con un ID por línea
        with open(path, 'r') as f:
            ids = [line.strip() for line in f if line.strip()]
        df = pd.DataFrame({'scholar_id': ids})

    # Buscar columna de ID
    id_col = None
    for col in ['scholar_id', 'id', 'google_scholar_id', 'ID']:
        if col in df.columns:
            id_col = col
            break

    if not id_col:
        logger.error("No se encontró columna de ID en el archivo")
        return 0

    for scholar_id in df[id_col]:
        if pd.isna(scholar_id):
            continue
        if add_by_id(str(scholar_id).strip(), authors, scraper):
            added += 1

    return added


def search_and_add(query: str, authors: dict, scraper: ScholarScraper) -> int:
    """Busca investigadores y permite agregarlos interactivamente."""
    from scholarly import scholarly

    added = 0
    try:
        search_query = scholarly.search_author(query)

        print(f"\nResultados para '{query}':\n")
        results = []

        for i, author in enumerate(search_query):
            if i >= 10:
                break
            results.append(author)
            print(f"{i+1}. {author.get('name', 'N/A')}")
            print(f"   Afiliación: {author.get('affiliation', 'N/A')}")
            print(f"   ID: {author.get('scholar_id', 'N/A')}")
            print()

        if not results:
            print("No se encontraron resultados.")
            return 0

        selection = input("Ingrese números a agregar (ej: 1,3,5) o 'todos' o 'cancelar': ")

        if selection.lower() == 'cancelar':
            return 0

        if selection.lower() == 'todos':
            indices = range(len(results))
        else:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]

        for idx in indices:
            if 0 <= idx < len(results):
                scholar_id = results[idx].get('scholar_id')
                if scholar_id and add_by_id(scholar_id, authors, scraper):
                    added += 1

    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")

    return added


def main():
    parser = argparse.ArgumentParser(description='Agregar investigadores al ranking')
    parser.add_argument('--id', type=str, help='ID de Google Scholar a agregar')
    parser.add_argument('--file', type=str, help='Archivo con lista de IDs')
    parser.add_argument('--search', type=str, help='Buscar por nombre/afiliación')

    args = parser.parse_args()

    # Cargar datos existentes
    authors = load_existing_authors()
    logger.info(f"Cargados {len(authors)} autores existentes")

    # Inicializar scraper
    scraper = ScholarScraper(delay_range=(2, 4))

    added = 0

    if args.id:
        if add_by_id(args.id, authors, scraper):
            added = 1

    elif args.file:
        added = add_from_file(args.file, authors, scraper)

    elif args.search:
        added = search_and_add(args.search, authors, scraper)

    else:
        parser.print_help()
        return

    if added > 0:
        save_authors(authors)
        print(f"\nAgregados {added} investigadores. Total: {len(authors)}")
    else:
        print("No se agregaron nuevos investigadores.")


if __name__ == "__main__":
    main()
