"""
Scraper usando SerpAPI para Google Scholar.
SerpAPI tiene un tier gratuito de 100 búsquedas/mes.

Para usar:
1. Crear cuenta en https://serpapi.com (gratis)
2. Obtener API key
3. Crear archivo .env con: SERPAPI_KEY=tu_api_key
   O pasar directamente al constructor
"""

import os
import json
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SerpAPIScholarScraper:
    """Scraper usando SerpAPI para Google Scholar."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str = None, delay: float = 1.0):
        """
        Inicializa el scraper.

        Args:
            api_key: API key de SerpAPI. Si no se provee, busca en SERPAPI_KEY env var
            delay: Delay entre requests en segundos
        """
        self.api_key = api_key or os.environ.get('SERPAPI_KEY')
        self.delay = delay

        if not self.api_key:
            logger.warning("No se encontró API key de SerpAPI. "
                          "Obtén una gratis en https://serpapi.com")

    def _make_request(self, params: dict) -> Optional[dict]:
        """Realiza request a SerpAPI."""
        if not self.api_key:
            logger.error("Se requiere API key de SerpAPI")
            return None

        params['api_key'] = self.api_key

        try:
            time.sleep(self.delay)
            response = requests.get(self.BASE_URL, params=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error HTTP {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error en request: {e}")
            return None

    def get_author_by_id(self, scholar_id: str) -> Optional[Dict]:
        """
        Obtiene datos de un autor por su ID.

        Args:
            scholar_id: ID de Google Scholar

        Returns:
            Diccionario con datos del autor
        """
        params = {
            'engine': 'google_scholar_author',
            'author_id': scholar_id,
            'hl': 'en'
        }

        result = self._make_request(params)

        if not result:
            return None

        try:
            author = result.get('author', {})
            cited_by = result.get('cited_by', {})

            # Extraer métricas de la tabla
            table = cited_by.get('table', [])
            metrics = {}
            for row in table:
                citations = row.get('citations', {})
                metrics[row.get('id', '')] = {
                    'all': citations.get('all', 0),
                    'since_2019': citations.get('since_2019', 0)
                }

            data = {
                'scholar_id': scholar_id,
                'name': author.get('name', ''),
                'affiliation': author.get('affiliations', ''),
                'email_domain': author.get('email', '').replace('Verified email at ', ''),
                'interests': [i.get('title', '') for i in author.get('interests', [])],
                'h_index': metrics.get('h_index', {}).get('all', 0),
                'h_index_5y': metrics.get('h_index', {}).get('since_2019', 0),
                'i10_index': metrics.get('i10_index', {}).get('all', 0),
                'i10_index_5y': metrics.get('i10_index', {}).get('since_2019', 0),
                'citations': metrics.get('citations', {}).get('all', 0),
                'citations_5y': metrics.get('citations', {}).get('since_2019', 0),
                'url_picture': author.get('thumbnail', ''),
                'homepage': author.get('website', ''),
                'cites_per_year': cited_by.get('graph', []),
                'extracted_at': datetime.now().isoformat()
            }

            logger.info(f"Extraído: {data['name']} (H-index: {data['h_index']})")
            return data

        except Exception as e:
            logger.error(f"Error parseando resultado: {e}")
            return None

    def search_authors(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Busca autores por query.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de IDs de autores encontrados
        """
        params = {
            'engine': 'google_scholar_profiles',
            'mauthors': query,
            'hl': 'en'
        }

        result = self._make_request(params)

        if not result:
            return []

        authors = []
        profiles = result.get('profiles', [])

        for profile in profiles[:max_results]:
            scholar_id = profile.get('author_id')
            if scholar_id:
                # Obtener datos completos
                author_data = self.get_author_by_id(scholar_id)
                if author_data:
                    authors.append(author_data)

        return authors

    def get_authors_from_ids(self, scholar_ids: List[str]) -> List[Dict]:
        """Obtiene datos de múltiples autores."""
        authors = []
        for scholar_id in scholar_ids:
            author = self.get_author_by_id(scholar_id)
            if author:
                authors.append(author)
        return authors


def main():
    """Test del scraper con SerpAPI."""
    print("=" * 60)
    print("SCRAPER CON SERPAPI")
    print("=" * 60)

    api_key = os.environ.get('SERPAPI_KEY')

    if not api_key:
        print("\nPara usar este scraper necesitas una API key de SerpAPI.")
        print("1. Ve a https://serpapi.com y crea una cuenta gratuita")
        print("2. Copia tu API key")
        print("3. Ejecuta: set SERPAPI_KEY=tu_api_key  (Windows)")
        print("   O: export SERPAPI_KEY=tu_api_key  (Linux/Mac)")
        print("\nEl tier gratuito incluye 100 búsquedas/mes.")
        return

    scraper = SerpAPIScholarScraper(api_key=api_key)

    # Test
    author = scraper.get_author_by_id("UknWOrEAAAAJ")
    if author:
        print(f"\nNombre: {author['name']}")
        print(f"H-index: {author['h_index']}")
        print(f"Citas: {author['citations']}")


if __name__ == "__main__":
    main()
