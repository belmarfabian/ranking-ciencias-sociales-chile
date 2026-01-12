"""
Módulo para cálculo de métricas y generación de ranking.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calcula métricas y genera rankings."""

    def __init__(self, authors: List[Dict]):
        """
        Inicializa con lista de autores.

        Args:
            authors: Lista de diccionarios con datos de autores
        """
        self.df = pd.DataFrame(authors)
        self._clean_data()

    def _clean_data(self):
        """Limpia y prepara los datos."""
        # Asegurar tipos numéricos
        numeric_cols = ['h_index', 'h_index_5y', 'i10_index', 'i10_index_5y',
                       'citations', 'citations_5y']

        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0).astype(int)

        # Eliminar duplicados por scholar_id
        if 'scholar_id' in self.df.columns:
            self.df = self.df.drop_duplicates(subset='scholar_id', keep='first')

        logger.info(f"Datos limpiados: {len(self.df)} autores únicos")

    def calculate_consistency_index(self) -> pd.Series:
        """
        Calcula un índice de consistencia (C-Index) simplificado.

        El C-Index evalúa qué tan consistente es el perfil basándose en:
        - Presencia de afiliación
        - Presencia de intereses/keywords
        - Coherencia entre h-index y citas
        - Presencia de email verificado

        Returns:
            Serie con C-Index (0-100) por autor
        """
        c_index = pd.Series(index=self.df.index, dtype=float)

        for idx, row in self.df.iterrows():
            score = 0

            # Tiene afiliación (20 puntos)
            if pd.notna(row.get('affiliation')) and len(str(row.get('affiliation', ''))) > 5:
                score += 20

            # Tiene intereses definidos (20 puntos)
            interests = row.get('interests', [])
            if interests and len(interests) > 0:
                score += 20

            # Tiene email verificado (20 puntos)
            if pd.notna(row.get('email_domain')) and len(str(row.get('email_domain', ''))) > 3:
                score += 20

            # Coherencia h-index/citas (20 puntos)
            h = row.get('h_index', 0)
            cites = row.get('citations', 0)
            if h > 0 and cites > 0:
                # Un h-index de N implica al menos N*N citas
                expected_min_cites = h * h
                if cites >= expected_min_cites * 0.5:  # Al menos 50% del mínimo teórico
                    score += 20

            # Tiene actividad reciente (20 puntos)
            h5y = row.get('h_index_5y', 0)
            if h5y > 0:
                score += 20

            c_index[idx] = score

        return c_index

    def calculate_impact_score(self) -> pd.Series:
        """
        Calcula un score de impacto compuesto.

        Combina:
        - H-index (40%)
        - Citas totales normalizadas (30%)
        - H-index 5 años (20%)
        - i10-index (10%)

        Returns:
            Serie con impact score normalizado (0-100)
        """
        # Normalizar cada métrica a 0-100
        def normalize(series):
            if series.max() == series.min():
                return pd.Series([50] * len(series), index=series.index)
            return ((series - series.min()) / (series.max() - series.min())) * 100

        h_norm = normalize(self.df['h_index'])
        cites_norm = normalize(self.df['citations'])
        h5y_norm = normalize(self.df['h_index_5y'])
        i10_norm = normalize(self.df['i10_index'])

        impact = (h_norm * 0.4 + cites_norm * 0.3 + h5y_norm * 0.2 + i10_norm * 0.1)

        return impact.round(2)

    def generate_ranking(self, sort_by: str = 'h_index',
                        ascending: bool = False) -> pd.DataFrame:
        """
        Genera el ranking ordenado.

        Args:
            sort_by: Columna por la cual ordenar
            ascending: Si ordenar ascendente

        Returns:
            DataFrame con ranking
        """
        # Calcular métricas adicionales
        self.df['c_index'] = self.calculate_consistency_index()
        self.df['impact_score'] = self.calculate_impact_score()

        # Ordenar
        ranking = self.df.sort_values(
            by=[sort_by, 'citations'],
            ascending=[ascending, ascending]
        ).reset_index(drop=True)

        # Agregar posición
        ranking['rank'] = range(1, len(ranking) + 1)

        # Reordenar columnas
        cols_order = [
            'rank', 'name', 'affiliation', 'h_index', 'citations',
            'h_index_5y', 'citations_5y', 'i10_index', 'i10_index_5y',
            'c_index', 'impact_score', 'interests', 'scholar_id',
            'email_domain', 'extracted_at'
        ]

        available_cols = [c for c in cols_order if c in ranking.columns]
        ranking = ranking[available_cols]

        return ranking

    def get_statistics(self) -> Dict:
        """
        Calcula estadísticas descriptivas del dataset.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            'total_authors': len(self.df),
            'h_index': {
                'mean': round(self.df['h_index'].mean(), 2),
                'median': round(self.df['h_index'].median(), 2),
                'std': round(self.df['h_index'].std(), 2),
                'max': int(self.df['h_index'].max()),
                'min': int(self.df['h_index'].min())
            },
            'citations': {
                'mean': round(self.df['citations'].mean(), 2),
                'median': round(self.df['citations'].median(), 2),
                'total': int(self.df['citations'].sum()),
                'max': int(self.df['citations'].max())
            },
            'affiliations': self.df['affiliation'].value_counts().head(20).to_dict(),
            'generated_at': datetime.now().isoformat()
        }

        return stats

    def get_top_by_discipline(self, n: int = 10) -> Dict[str, pd.DataFrame]:
        """
        Obtiene top N por disciplina/interés.

        Args:
            n: Número de autores por disciplina

        Returns:
            Diccionario con DataFrames por disciplina
        """
        discipline_rankings = {}

        # Extraer todas las disciplinas únicas
        all_interests = []
        for interests in self.df['interests']:
            if isinstance(interests, list):
                all_interests.extend([i.lower() for i in interests])

        # Contar y tomar las más comunes
        from collections import Counter
        common_interests = Counter(all_interests).most_common(15)

        for interest, count in common_interests:
            if count >= 3:  # Al menos 3 autores
                mask = self.df['interests'].apply(
                    lambda x: any(interest in i.lower() for i in (x if isinstance(x, list) else []))
                )
                subset = self.df[mask].nlargest(n, 'h_index')
                if len(subset) > 0:
                    discipline_rankings[interest] = subset[['name', 'affiliation', 'h_index', 'citations']]

        return discipline_rankings


def main():
    """Ejemplo de uso."""
    # Datos de ejemplo
    sample_authors = [
        {
            'scholar_id': 'abc123',
            'name': 'Investigador Ejemplo',
            'affiliation': 'Universidad de Chile',
            'h_index': 25,
            'h_index_5y': 15,
            'citations': 3000,
            'citations_5y': 1500,
            'i10_index': 40,
            'i10_index_5y': 20,
            'interests': ['sociología', 'política'],
            'email_domain': 'uchile.cl'
        }
    ]

    calc = MetricsCalculator(sample_authors)
    ranking = calc.generate_ranking()
    print(ranking)


if __name__ == "__main__":
    main()
