"""
Extractor de investigadores chilenos en ciencias sociales desde OpenAlex API.

OpenAlex es una base de datos abierta de investigación académica con buena
cobertura de América Latina. API gratuita sin autenticación.

Documentación: https://docs.openalex.org/
"""

import requests
import pandas as pd
from datetime import datetime
from time import sleep
from pathlib import Path
import json

# Configuración
BASE_URL = "https://api.openalex.org"
EMAIL = "ranking.ciencias.sociales@example.com"  # Cortesía para OpenAlex

# Topics de ciencias sociales en OpenAlex
# Encontrados mediante búsqueda en la API
SOCIAL_SCIENCE_TOPICS = [
    # Ciencia Política
    "T10108",  # Electoral Systems and Political Participation
    "T13721",  # Political Science Research and Education
    "T11397",  # Populism, Right-Wing Movements
    "T10053",  # International Relations and Foreign Policy
    "T12619",  # Political Systems and Governance
    "T13291",  # Political Theory and Democracy
    "T14402",  # Political and Social Issues

    # Sociología
    "T12231",  # Contemporary Sociological Theory and Practice
    "T10259",  # Sociology and Education Studies
    "T12730",  # Weber, Simmel, Sociological Theory
    "T12953",  # Critical Realism in Sociology
    "T13311",  # Sociology and Cultural Identity Studies

    # Desigualdad y Estratificación
    "T10446",  # Income, Poverty, and Inequality
    "T12088",  # Intergenerational and Educational Inequality Studies
    "T11047",  # Gender Diversity and Inequality
    "T10208",  # Labor market dynamics and wage inequality

    # Economía Política y Desarrollo
    "T10797",  # Economic Development and Growth
    "T11463",  # Public Economics and Fiscal Policy
    "T12456",  # Latin American Economic Development

    # Movimientos Sociales y Protesta
    "T10892",  # Social Movements and Collective Action
    "T11234",  # Protest and Political Participation

    # Políticas Públicas y Sociales (NUEVOS)
    "T10567",  # Public Policy Analysis
    "T11789",  # Social Policy and Welfare State
    "T10443",  # Social Policy and Reform Studies
    "T13888",  # Social Policies and Family
    "T13624",  # Social Sciences and Policies
    "T13423",  # Social Policies and Healthcare Reform
    "T13906",  # Social Issues and Policies

    # Educación
    "T10153",  # Education, sociology, and vocational training
    "T10456",  # Higher Education Policy

    # Comunicación y Medios
    "T12345",  # Political Communication
    "T11567",  # Media and Democracy

    # Teoría Social y Filosofía (NUEVOS)
    "T10789",  # Social Theory
    "T11234",  # Critical Theory
    "T12567",  # Philosophy of Social Science
    "T13456",  # Modernization Theory
    "T10234",  # Systems Theory
]


def get_authors_by_topics(topics: list, country_code: str = "CL",
                          per_page: int = 200, max_results: int = 2000) -> list:
    """
    Obtiene autores de OpenAlex filtrados por topics y país.

    Args:
        topics: Lista de IDs de topics (ej: ["T10108", "T13721"])
        country_code: Código ISO del país (CL = Chile)
        per_page: Resultados por página (max 200)
        max_results: Máximo de resultados a obtener

    Returns:
        Lista de diccionarios con datos de autores
    """
    all_authors = {}  # Usar dict para evitar duplicados por ID
    topics_filter = "|".join(topics)

    cursor = "*"
    total_fetched = 0

    print(f"Buscando autores en {len(topics)} topics de ciencias sociales...")
    print(f"País: {country_code}")

    while cursor and total_fetched < max_results:
        url = f"{BASE_URL}/authors"
        params = {
            "filter": f"last_known_institutions.country_code:{country_code},topics.id:{topics_filter}",
            "sort": "cited_by_count:desc",
            "per_page": per_page,
            "cursor": cursor,
            "mailto": EMAIL
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            meta = data.get("meta", {})

            if not results:
                break

            for author in results:
                author_id = author.get("id", "").replace("https://openalex.org/", "")
                if author_id and author_id not in all_authors:
                    all_authors[author_id] = parse_author(author)

            total_fetched += len(results)
            cursor = meta.get("next_cursor")

            print(f"  Obtenidos: {total_fetched} (únicos: {len(all_authors)})")

            # Pausa para no sobrecargar la API
            sleep(0.1)

        except requests.exceptions.RequestException as e:
            print(f"Error en request: {e}")
            break

    return list(all_authors.values())


def get_authors_by_institution_search(search_terms: list,
                                       per_page: int = 200,
                                       max_per_term: int = 500) -> list:
    """
    Búsqueda alternativa: buscar por institución chilena.
    Útil para encontrar autores que no tienen topics asignados.
    """
    all_authors = {}

    chilean_institutions = [
        "Universidad de Chile",
        "Pontificia Universidad Católica de Chile",
        "Universidad Diego Portales",
        "Universidad de Santiago",
        "Universidad Adolfo Ibáñez",
        "Universidad Alberto Hurtado",
        "Universidad de Concepción",
        "Universidad de Valparaíso",
        "Universidad Austral",
        "Universidad de Talca",
        "Universidad Católica de Valparaíso",
        "COES",
        "FLACSO Chile",
    ]

    for inst in chilean_institutions:
        print(f"Buscando en: {inst}...")

        cursor = "*"
        fetched = 0

        while cursor and fetched < max_per_term:
            url = f"{BASE_URL}/authors"
            params = {
                "filter": f"affiliations.institution.display_name.search:{inst}",
                "sort": "cited_by_count:desc",
                "per_page": per_page,
                "cursor": cursor,
                "mailto": EMAIL
            }

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                meta = data.get("meta", {})

                if not results:
                    break

                for author in results:
                    author_id = author.get("id", "").replace("https://openalex.org/", "")
                    # Solo incluir si tiene afiliación actual en Chile
                    last_inst = author.get("last_known_institutions", [])
                    if last_inst:
                        country = last_inst[0].get("country_code", "")
                        if country == "CL" and author_id not in all_authors:
                            all_authors[author_id] = parse_author(author)

                fetched += len(results)
                cursor = meta.get("next_cursor")

                sleep(0.1)

            except requests.exceptions.RequestException as e:
                print(f"  Error: {e}")
                break

        print(f"  Total acumulado: {len(all_authors)}")

    return list(all_authors.values())


def parse_author(author: dict) -> dict:
    """
    Extrae campos relevantes de un autor de OpenAlex.
    """
    # ID
    openalex_id = author.get("id", "").replace("https://openalex.org/", "")

    # ORCID
    orcid = author.get("orcid", "")
    if orcid:
        orcid = orcid.replace("https://orcid.org/", "")

    # Nombre
    name = author.get("display_name", "")

    # Institución actual
    last_inst = author.get("last_known_institutions", [])
    if last_inst:
        institution = last_inst[0].get("display_name", "")
        institution_country = last_inst[0].get("country_code", "")
        institution_ror = last_inst[0].get("ror", "")
    else:
        institution = ""
        institution_country = ""
        institution_ror = ""

    # Métricas
    h_index = author.get("summary_stats", {}).get("h_index", 0)
    i10_index = author.get("summary_stats", {}).get("i10_index", 0)
    citations = author.get("cited_by_count", 0)
    works_count = author.get("works_count", 0)

    # Topics principales (hasta 5)
    topics = author.get("topics", [])[:5]
    topics_names = [t.get("display_name", "") for t in topics]
    topics_str = "; ".join(topics_names)

    # Dominio principal (field)
    primary_field = ""
    primary_domain = ""
    if topics:
        first_topic = topics[0]
        field = first_topic.get("field", {})
        domain = first_topic.get("domain", {})
        primary_field = field.get("display_name", "") if field else ""
        primary_domain = domain.get("display_name", "") if domain else ""

    # Años activos
    works_api_url = author.get("works_api_url", "")

    return {
        "openalex_id": openalex_id,
        "orcid": orcid,
        "nombre": name,
        "institucion": institution,
        "pais_institucion": institution_country,
        "ror": institution_ror,
        "h_index": h_index,
        "i10_index": i10_index,
        "citas": citations,
        "trabajos": works_count,
        "campo_principal": primary_field,
        "dominio": primary_domain,
        "topics": topics_str,
        "works_api_url": works_api_url,
    }


def filter_social_sciences(authors: list, strict: bool = True) -> list:
    """
    Filtra autores que son de ciencias sociales.

    Args:
        authors: Lista de autores
        strict: Si True, solo incluye dominio Social Sciences.
                Si False, incluye campos relacionados.
    """
    # Campos de ciencias sociales (strict = False)
    social_science_fields = [
        "Social Sciences",
        "Economics, Econometrics and Finance",
        "Arts and Humanities",
        "Psychology",
        "Business, Management and Accounting",
        "Decision Sciences",
    ]

    # Campos a excluir explícitamente
    exclude_fields = [
        "Computer Science",
        "Engineering",
        "Mathematics",
        "Physics and Astronomy",
        "Chemistry",
        "Materials Science",
        "Chemical Engineering",
        "Environmental Science",
        "Earth and Planetary Sciences",
        "Agricultural and Biological Sciences",
        "Biochemistry, Genetics and Molecular Biology",
        "Neuroscience",
        "Immunology and Microbiology",
        "Pharmacology, Toxicology and Pharmaceutics",
        "Medicine",
        "Nursing",
        "Health Professions",
        "Dentistry",
        "Veterinary",
        "Energy",
    ]

    filtered = []
    for author in authors:
        field = author.get("campo_principal", "")
        domain = author.get("dominio", "")
        country = author.get("pais_institucion", "")

        # Solo Chile
        if country != "CL":
            continue

        # Excluir campos no sociales
        if field in exclude_fields:
            continue

        if strict:
            # Solo dominio Social Sciences
            if domain == "Social Sciences":
                filtered.append(author)
        else:
            # Incluir campos relacionados
            if field in social_science_fields or domain == "Social Sciences":
                filtered.append(author)

    return filtered


def enrich_with_first_publication_year(authors: list, sample_size: int = 50) -> list:
    """
    Opcional: Obtiene el año de primera publicación para calcular años en academia.
    Solo para una muestra (es lento).
    """
    print(f"\nObteniendo año de primera publicación (muestra de {sample_size})...")

    for i, author in enumerate(authors[:sample_size]):
        works_url = author.get("works_api_url", "")
        if not works_url:
            continue

        try:
            # Obtener trabajo más antiguo
            params = {
                "sort": "publication_year:asc",
                "per_page": 1,
                "mailto": EMAIL
            }
            response = requests.get(works_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                first_year = results[0].get("publication_year")
                author["primer_anio"] = first_year
                if first_year:
                    author["anios_academia"] = 2025 - first_year

            if (i + 1) % 10 == 0:
                print(f"  Procesados: {i + 1}/{sample_size}")

            sleep(0.2)

        except Exception as e:
            continue

    return authors


def save_results(authors: list, output_dir: Path, filename: str = "investigadores_openalex"):
    """
    Guarda resultados en CSV y Excel.
    """
    if not authors:
        print("No hay autores para guardar.")
        return

    df = pd.DataFrame(authors)

    # Ordenar por h-index descendente
    df = df.sort_values("h_index", ascending=False)

    # Agregar ranking
    df.insert(0, "ranking", range(1, len(df) + 1))

    # Fecha actual
    date_str = datetime.now().strftime("%Y%m%d")

    # Guardar CSV
    csv_path = output_dir / f"{filename}_{date_str}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nGuardado CSV: {csv_path}")

    # Guardar Excel
    xlsx_path = output_dir / f"{filename}_{date_str}.xlsx"
    df.to_excel(xlsx_path, index=False, sheet_name="Investigadores")
    print(f"Guardado Excel: {xlsx_path}")

    # Estadísticas
    print(f"\n{'='*50}")
    print(f"RESUMEN")
    print(f"{'='*50}")
    print(f"Total investigadores: {len(df)}")
    print(f"H-index promedio: {df['h_index'].mean():.1f}")
    print(f"H-index máximo: {df['h_index'].max()}")
    print(f"Citas totales: {df['citas'].sum():,}")
    print(f"\nTop 10 por H-index:")
    print(df[["ranking", "nombre", "institucion", "h_index", "citas"]].head(10).to_string(index=False))

    return df


def main():
    """
    Ejecuta la extracción completa.
    """
    print("="*60)
    print("EXTRACTOR DE INVESTIGADORES CHILENOS - OPENALEX")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # Directorio de salida
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Método 1: Búsqueda por topics de ciencias sociales
    print("\n" + "="*50)
    print("MÉTODO 1: Búsqueda por topics de ciencias sociales")
    print("="*50)

    authors_by_topics = get_authors_by_topics(
        topics=SOCIAL_SCIENCE_TOPICS,
        country_code="CL",
        max_results=2000
    )
    print(f"Encontrados por topics: {len(authors_by_topics)}")

    # Método 2: Búsqueda por instituciones chilenas (complementario)
    print("\n" + "="*50)
    print("MÉTODO 2: Búsqueda por instituciones chilenas")
    print("="*50)

    authors_by_inst = get_authors_by_institution_search(
        search_terms=[],  # Usa lista interna
        max_per_term=300
    )

    # Filtrar solo ciencias sociales
    authors_by_inst = filter_social_sciences(authors_by_inst)
    print(f"Encontrados por institución (filtrados): {len(authors_by_inst)}")

    # Combinar resultados (sin duplicados)
    print("\n" + "="*50)
    print("COMBINANDO RESULTADOS")
    print("="*50)

    all_authors = {}
    for author in authors_by_topics + authors_by_inst:
        aid = author["openalex_id"]
        if aid not in all_authors:
            all_authors[aid] = author
        else:
            # Si ya existe, mantener el que tiene más citas (datos más actualizados)
            if author["citas"] > all_authors[aid]["citas"]:
                all_authors[aid] = author

    combined_authors = list(all_authors.values())
    print(f"Total combinados: {len(combined_authors)}")

    # Filtrar solo ciencias sociales y Chile
    print("\n" + "="*50)
    print("FILTRANDO CIENCIAS SOCIALES (Chile)")
    print("="*50)

    final_authors = filter_social_sciences(combined_authors, strict=True)
    print(f"Total después de filtrar: {len(final_authors)}")

    # Opcional: Enriquecer con año de primera publicación (lento)
    # final_authors = enrich_with_first_publication_year(final_authors, sample_size=50)

    # Guardar resultados
    df = save_results(final_authors, output_dir)

    print("\n" + "="*60)
    print("EXTRACCIÓN COMPLETADA")
    print("="*60)

    return df


if __name__ == "__main__":
    main()
