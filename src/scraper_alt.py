"""
Scraper alternativo de Google Scholar usando requests directo.
Se usa cuando scholarly falla por bloqueos.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScholarScraperAlt:
    """Scraper alternativo usando requests directo."""

    BASE_URL = "https://scholar.google.com"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(self, delay_range: tuple = (5, 10)):
        """
        Inicializa el scraper.

        Args:
            delay_range: Rango de delay entre requests
        """
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _random_delay(self):
        """Delay aleatorio entre requests."""
        delay = random.uniform(*self.delay_range)
        logger.info(f"Esperando {delay:.1f} segundos...")
        time.sleep(delay)

    def get_author_by_id(self, scholar_id: str) -> Optional[Dict]:
        """
        Obtiene datos de un autor por su ID de Scholar.

        Args:
            scholar_id: ID de Google Scholar

        Returns:
            Diccionario con datos del autor
        """
        url = f"{self.BASE_URL}/citations?user={scholar_id}&hl=en"

        try:
            self._random_delay()
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code} para {scholar_id}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Verificar si hay CAPTCHA o bloqueo
            if 'unusual traffic' in response.text.lower() or 'captcha' in response.text.lower():
                logger.error("Detectado CAPTCHA o bloqueo de Google Scholar")
                return None

            # Extraer datos
            data = self._parse_author_page(soup, scholar_id)
            return data

        except Exception as e:
            logger.error(f"Error obteniendo autor {scholar_id}: {e}")
            return None

    def _parse_author_page(self, soup: BeautifulSoup, scholar_id: str) -> Optional[Dict]:
        """
        Parsea la página de un autor.

        Args:
            soup: BeautifulSoup de la página
            scholar_id: ID del autor

        Returns:
            Diccionario con datos
        """
        try:
            # Nombre
            name_elem = soup.find('div', {'id': 'gsc_prf_in'})
            name = name_elem.text.strip() if name_elem else ''

            # Afiliación
            affil_elem = soup.find('div', {'class': 'gsc_prf_il'})
            affiliation = affil_elem.text.strip() if affil_elem else ''

            # Email domain
            email_elem = soup.find('div', {'id': 'gsc_prf_ivh'})
            email_domain = ''
            if email_elem:
                email_text = email_elem.text
                if '@' in email_text:
                    email_domain = email_text.split('@')[-1].strip()
                elif 'Verified email at' in email_text:
                    email_domain = email_text.replace('Verified email at', '').strip()

            # Intereses/Keywords
            interests = []
            interest_elems = soup.find_all('a', {'class': 'gsc_prf_inta'})
            for elem in interest_elems:
                interests.append(elem.text.strip())

            # Métricas (tabla de índices)
            h_index = 0
            h_index_5y = 0
            i10_index = 0
            i10_index_5y = 0
            citations = 0
            citations_5y = 0

            # Buscar tabla de métricas
            metrics_table = soup.find('table', {'id': 'gsc_rsb_st'})
            if metrics_table:
                rows = metrics_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        metric_name = cells[0].text.strip().lower()
                        all_val = cells[1].text.strip()
                        since_val = cells[2].text.strip() if len(cells) > 2 else '0'

                        try:
                            if 'citations' in metric_name:
                                citations = int(all_val) if all_val else 0
                                citations_5y = int(since_val) if since_val else 0
                            elif 'h-index' in metric_name:
                                h_index = int(all_val) if all_val else 0
                                h_index_5y = int(since_val) if since_val else 0
                            elif 'i10-index' in metric_name:
                                i10_index = int(all_val) if all_val else 0
                                i10_index_5y = int(since_val) if since_val else 0
                        except ValueError:
                            pass

            # URL de foto
            pic_elem = soup.find('img', {'id': 'gsc_prf_pup-img'})
            url_picture = pic_elem.get('src', '') if pic_elem else ''

            # Homepage
            homepage = ''
            homepage_elem = soup.find('a', {'class': 'gsc_prf_ila'})
            if homepage_elem:
                homepage = homepage_elem.get('href', '')

            data = {
                'scholar_id': scholar_id,
                'name': name,
                'affiliation': affiliation,
                'email_domain': email_domain,
                'interests': interests,
                'h_index': h_index,
                'h_index_5y': h_index_5y,
                'i10_index': i10_index,
                'i10_index_5y': i10_index_5y,
                'citations': citations,
                'citations_5y': citations_5y,
                'url_picture': url_picture,
                'homepage': homepage,
                'cites_per_year': {},
                'extracted_at': datetime.now().isoformat()
            }

            logger.info(f"Extraído: {name} (H-index: {h_index}, Citas: {citations})")
            return data

        except Exception as e:
            logger.error(f"Error parseando página: {e}")
            return None

    def search_authors(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Busca autores por query.

        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados

        Returns:
            Lista de autores encontrados
        """
        authors = []
        url = f"{self.BASE_URL}/citations?hl=en&view_op=search_authors&mauthors={requests.utils.quote(query)}"

        try:
            self._random_delay()
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code}")
                return authors

            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar resultados de autores
            author_divs = soup.find_all('div', {'class': 'gsc_1usr'})

            for div in author_divs[:max_results]:
                try:
                    # Extraer ID del autor
                    link = div.find('a', {'class': 'gs_ai_pho'})
                    if not link:
                        link = div.find('a')

                    if link and 'user=' in link.get('href', ''):
                        href = link.get('href', '')
                        scholar_id = re.search(r'user=([^&]+)', href)
                        if scholar_id:
                            scholar_id = scholar_id.group(1)

                            # Obtener datos completos
                            author_data = self.get_author_by_id(scholar_id)
                            if author_data:
                                authors.append(author_data)

                except Exception as e:
                    logger.warning(f"Error procesando resultado: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")

        return authors

    def get_authors_from_ids(self, scholar_ids: List[str]) -> List[Dict]:
        """
        Obtiene datos de múltiples autores por sus IDs.

        Args:
            scholar_ids: Lista de IDs de Scholar

        Returns:
            Lista de autores
        """
        authors = []

        for scholar_id in scholar_ids:
            author = self.get_author_by_id(scholar_id)
            if author:
                authors.append(author)

        return authors

    def save_results(self, authors: List[Dict], filepath: str):
        """Guarda resultados en JSON."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(authors, f, ensure_ascii=False, indent=2)
        logger.info(f"Guardados {len(authors)} autores en {filepath}")


def main():
    """Test del scraper alternativo."""
    scraper = ScholarScraperAlt(delay_range=(3, 5))

    # Test: obtener autor por ID
    print("=" * 50)
    print("Test: Obtener autor por ID")
    print("=" * 50)

    author = scraper.get_author_by_id("UknWOrEAAAAJ")

    if author:
        print(f"Nombre: {author['name']}")
        print(f"Afiliación: {author['affiliation']}")
        print(f"H-index: {author['h_index']}")
        print(f"Citas: {author['citations']}")
        print(f"Intereses: {', '.join(author['interests'][:5])}")
        print("\nTEST EXITOSO")
    else:
        print("No se pudo obtener el autor (posible bloqueo)")


if __name__ == "__main__":
    main()
