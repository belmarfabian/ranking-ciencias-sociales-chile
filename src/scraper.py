"""
Scraper de Google Scholar para científicos sociales chilenos.
Utiliza la librería scholarly para extraer datos de perfiles.
"""

import time
import random
import logging
from typing import Optional, Dict, List, Any
from scholarly import scholarly, ProxyGenerator
from tqdm import tqdm
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScholarScraper:
    """Clase para extraer datos de Google Scholar."""

    def __init__(self, use_proxy: bool = True, delay_range: tuple = (3, 7)):
        """
        Inicializa el scraper.

        Args:
            use_proxy: Si usar proxy para evitar bloqueos
            delay_range: Rango de delay entre requests (min, max) en segundos
        """
        self.delay_range = delay_range
        self.results = []

        # Configurar headers para parecer un navegador real
        self._setup_scholarly()

        if use_proxy:
            self._setup_proxy()

    def _setup_scholarly(self):
        """Configura scholarly con headers más realistas."""
        try:
            # Intentar configurar con ScraperAPI si hay key disponible
            # Por ahora usar configuración básica
            pass
        except Exception as e:
            logger.warning(f"Error en setup: {e}")

    def _setup_proxy(self):
        """Configura proxy gratuito para evitar bloqueos."""
        try:
            pg = ProxyGenerator()
            # Intentar con FreeProxies primero
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                logger.info("Proxy configurado exitosamente")
            else:
                logger.warning("No se pudo configurar proxy, continuando sin proxy")
        except Exception as e:
            logger.warning(f"No se pudo configurar proxy: {e}")

    def _random_delay(self):
        """Aplica un delay aleatorio entre requests."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def search_by_affiliation(self, affiliation: str, max_results: int = 100) -> List[Dict]:
        """
        Busca autores por afiliación.

        Args:
            affiliation: Nombre de la institución
            max_results: Máximo de resultados a retornar

        Returns:
            Lista de diccionarios con datos de autores
        """
        authors = []
        try:
            search_query = scholarly.search_author(affiliation)

            for i, author in enumerate(search_query):
                if i >= max_results:
                    break

                try:
                    # Obtener perfil completo
                    author_data = self._extract_author_data(author)
                    if author_data:
                        authors.append(author_data)
                        logger.info(f"Extraído: {author_data.get('name', 'Unknown')}")

                    self._random_delay()

                except Exception as e:
                    logger.warning(f"Error extrayendo autor: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error buscando por afiliación {affiliation}: {e}")

        return authors

    def search_by_keyword_and_location(self, keyword: str, location: str = "Chile",
                                        max_results: int = 50) -> List[Dict]:
        """
        Busca autores por keyword y ubicación.

        Args:
            keyword: Palabra clave (disciplina)
            location: Ubicación geográfica
            max_results: Máximo de resultados

        Returns:
            Lista de autores encontrados
        """
        authors = []
        search_term = f"{keyword} {location}"

        try:
            search_query = scholarly.search_author(search_term)

            for i, author in enumerate(search_query):
                if i >= max_results:
                    break

                try:
                    author_data = self._extract_author_data(author)
                    if author_data and self._is_chilean(author_data):
                        authors.append(author_data)
                        logger.info(f"Encontrado: {author_data.get('name', 'Unknown')}")

                    self._random_delay()

                except Exception as e:
                    logger.warning(f"Error: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error buscando {keyword}: {e}")

        return authors

    def get_author_by_id(self, scholar_id: str) -> Optional[Dict]:
        """
        Obtiene datos de un autor por su ID de Scholar.

        Args:
            scholar_id: ID de Google Scholar del autor

        Returns:
            Diccionario con datos del autor o None
        """
        try:
            self._random_delay()
            author = scholarly.search_author_id(scholar_id)

            if author is None:
                logger.warning(f"No se encontró autor con ID: {scholar_id}")
                return None

            # Intentar llenar datos adicionales
            try:
                author_filled = scholarly.fill(author, sections=['basics', 'indices', 'counts'])
            except Exception as fill_error:
                logger.warning(f"No se pudieron obtener datos completos: {fill_error}")
                author_filled = author

            return self._extract_author_data(author_filled, already_filled=True)
        except Exception as e:
            logger.error(f"Error obteniendo autor {scholar_id}: {e}")
            return None

    def _extract_author_data(self, author, already_filled: bool = False) -> Optional[Dict]:
        """
        Extrae datos relevantes de un autor.

        Args:
            author: Objeto autor de scholarly
            already_filled: Si el autor ya tiene datos completos

        Returns:
            Diccionario con datos procesados
        """
        try:
            if author is None:
                return None

            # Convertir a dict si es necesario
            if hasattr(author, '__dict__'):
                author_dict = dict(author)
            elif isinstance(author, dict):
                author_dict = author
            else:
                logger.warning(f"Tipo de autor no reconocido: {type(author)}")
                return None

            if not already_filled:
                try:
                    author = scholarly.fill(author, sections=['basics', 'indices', 'counts'])
                    if hasattr(author, '__dict__'):
                        author_dict = dict(author)
                    elif isinstance(author, dict):
                        author_dict = author
                except Exception as e:
                    logger.warning(f"No se pudo llenar autor: {e}")

            # Extraer métricas de forma segura
            def safe_get(d, key, default=None):
                try:
                    val = d.get(key, default) if isinstance(d, dict) else getattr(d, key, default)
                    return val if val is not None else default
                except:
                    return default

            data = {
                'scholar_id': safe_get(author_dict, 'scholar_id', ''),
                'name': safe_get(author_dict, 'name', ''),
                'affiliation': safe_get(author_dict, 'affiliation', ''),
                'email_domain': safe_get(author_dict, 'email_domain', ''),
                'interests': safe_get(author_dict, 'interests', []) or [],
                'h_index': safe_get(author_dict, 'hindex', 0) or 0,
                'h_index_5y': safe_get(author_dict, 'hindex5y', 0) or 0,
                'i10_index': safe_get(author_dict, 'i10index', 0) or 0,
                'i10_index_5y': safe_get(author_dict, 'i10index5y', 0) or 0,
                'citations': safe_get(author_dict, 'citedby', 0) or 0,
                'citations_5y': safe_get(author_dict, 'citedby5y', 0) or 0,
                'url_picture': safe_get(author_dict, 'url_picture', ''),
                'homepage': safe_get(author_dict, 'homepage', ''),
                'cites_per_year': safe_get(author_dict, 'cites_per_year', {}) or {},
                'extracted_at': datetime.now().isoformat()
            }

            # Validar que al menos tenemos nombre o ID
            if not data['name'] and not data['scholar_id']:
                return None

            return data

        except Exception as e:
            logger.warning(f"Error extrayendo datos: {e}")
            return None

    def _is_chilean(self, author_data: Dict) -> bool:
        """
        Verifica si un autor tiene afiliación chilena.

        Args:
            author_data: Diccionario con datos del autor

        Returns:
            True si tiene afiliación chilena
        """
        chile_keywords = [
            'chile', 'chilena', 'chileno', 'santiago', 'valparaíso',
            'concepción', 'uchile', 'puc', 'udp', 'uai', 'usach'
        ]

        affiliation = author_data.get('affiliation', '').lower()
        email = author_data.get('email_domain', '').lower()

        for keyword in chile_keywords:
            if keyword in affiliation or keyword in email:
                return True

        # Verificar dominios .cl
        if '.cl' in email:
            return True

        return False

    def search_comprehensive(self, disciplines: List[str], universities: List[str],
                            max_per_search: int = 50) -> List[Dict]:
        """
        Realiza búsqueda comprehensiva por disciplinas y universidades.

        Args:
            disciplines: Lista de disciplinas a buscar
            universities: Lista de universidades
            max_per_search: Máximo de resultados por búsqueda

        Returns:
            Lista consolidada de autores (sin duplicados)
        """
        all_authors = {}

        # Buscar por universidad
        logger.info("=== Buscando por universidades ===")
        for uni in tqdm(universities, desc="Universidades"):
            authors = self.search_by_affiliation(uni, max_results=max_per_search)
            for author in authors:
                scholar_id = author.get('scholar_id')
                if scholar_id and scholar_id not in all_authors:
                    # Filtrar solo ciencias sociales
                    if self._is_social_science(author, disciplines):
                        all_authors[scholar_id] = author

            self._random_delay()

        # Buscar por disciplina + Chile
        logger.info("=== Buscando por disciplinas ===")
        for discipline in tqdm(disciplines, desc="Disciplinas"):
            authors = self.search_by_keyword_and_location(discipline, "Chile", max_per_search)
            for author in authors:
                scholar_id = author.get('scholar_id')
                if scholar_id and scholar_id not in all_authors:
                    all_authors[scholar_id] = author

            self._random_delay()

        return list(all_authors.values())

    def _is_social_science(self, author_data: Dict, disciplines: List[str]) -> bool:
        """
        Verifica si un autor es de ciencias sociales.

        Args:
            author_data: Datos del autor
            disciplines: Lista de disciplinas válidas

        Returns:
            True si es de ciencias sociales
        """
        interests = [i.lower() for i in author_data.get('interests', [])]
        affiliation = author_data.get('affiliation', '').lower()

        disciplines_lower = [d.lower() for d in disciplines]

        for interest in interests:
            for discipline in disciplines_lower:
                if discipline in interest or interest in discipline:
                    return True

        for discipline in disciplines_lower:
            if discipline in affiliation:
                return True

        return False

    def save_results(self, authors: List[Dict], filepath: str):
        """
        Guarda resultados en archivo JSON.

        Args:
            authors: Lista de autores
            filepath: Ruta del archivo
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(authors, f, ensure_ascii=False, indent=2)

        logger.info(f"Guardados {len(authors)} autores en {filepath}")


def main():
    """Función principal de ejemplo."""
    scraper = ScholarScraper(use_proxy=False, delay_range=(3, 7))

    # Ejemplo: buscar un autor específico
    # author = scraper.get_author_by_id("UknWOrEAAAAJ")  # Bastián González-Bustamante
    # print(json.dumps(author, indent=2, ensure_ascii=False))

    # Ejemplo: buscar por disciplina
    authors = scraper.search_by_keyword_and_location("sociología", "Chile", max_results=10)
    print(f"Encontrados: {len(authors)} autores")

    for author in authors:
        print(f"  - {author['name']} (H-index: {author['h_index']})")


if __name__ == "__main__":
    main()
