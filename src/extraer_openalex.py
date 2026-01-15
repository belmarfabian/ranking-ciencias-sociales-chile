"""
Extrae datos de investigadores chilenos en ciencias sociales desde la API de OpenAlex.

La API de OpenAlex es gratuita y no requiere autenticación.
Documentación: https://docs.openalex.org/

Uso:
    python src/extraer_openalex.py

Genera:
    data/raw/investigadores_openalex_YYYYMMDD.csv
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from time import sleep

# Configuración
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMAIL = "ranking.ciencias.sociales@example.com"
API_BASE = "https://api.openalex.org"

# H-index mínimo para descargar (reduce cantidad de datos)
H_INDEX_MIN_DOWNLOAD = 1

# Dominios de ciencias sociales
DOMINIOS_CS = {"Social Sciences"}

# Campos específicos de ciencias sociales
CAMPOS_CS = {
    "Sociology", "Political Science", "Economics", "Psychology",
    "Education", "Law", "Business", "Geography", "Anthropology",
    "Communication", "Social Work", "Public Policy", "Demography",
    "Gender Studies", "Urban Studies", "Development Studies",
    "Public Administration", "Social Psychology", "Criminology",
    "Political Economy", "International Relations",
}


def es_ciencias_sociales(author):
    """Determina si un autor es de ciencias sociales."""
    topics = author.get("topics", [])

    # Revisar los primeros 5 topics
    for topic in topics[:5]:
        domain = topic.get("domain", {}).get("display_name", "")
        field = topic.get("field", {}).get("display_name", "")

        if domain in DOMINIOS_CS:
            return True, field

        if field in CAMPOS_CS:
            return True, field

    # Revisar x_concepts como backup
    x_concepts = author.get("x_concepts", [])
    for concept in x_concepts[:10]:
        name = concept.get("display_name", "")
        score = concept.get("score", 0)
        if score > 40 and name in CAMPOS_CS:
            return True, name

    return False, ""


def get_authors_chile():
    """Obtiene autores chilenos con h-index >= 1 y filtra ciencias sociales."""
    print(f"Descargando autores de Chile con h-index > {H_INDEX_MIN_DOWNLOAD}...")

    all_authors = []
    cursor = "*"
    page = 0
    cs_count = 0

    while cursor:
        url = f"{API_BASE}/authors"
        params = {
            "filter": f"last_known_institutions.country_code:cl,summary_stats.h_index:>{H_INDEX_MIN_DOWNLOAD}",
            "per_page": 200,
            "cursor": cursor,
            "mailto": EMAIL,
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                break

            for author in results:
                # Verificar si es ciencias sociales
                es_cs, campo = es_ciencias_sociales(author)
                if not es_cs:
                    continue

                # Extraer datos
                summary = author.get("summary_stats", {})
                last_inst = author.get("last_known_institutions", [])

                inst_name = ""
                for inst in last_inst:
                    if inst.get("country_code") == "CL":
                        inst_name = inst.get("display_name", "")
                        break

                if not inst_name:
                    continue

                author_data = {
                    "openalex_id": author.get("id", ""),
                    "nombre": author.get("display_name", ""),
                    "orcid": (author.get("orcid") or "").replace("https://orcid.org/", ""),
                    "h_index": summary.get("h_index", 0),
                    "i10_index": summary.get("i10_index", 0),
                    "cited_by_count": author.get("cited_by_count", 0),
                    "works_count": author.get("works_count", 0),
                    "2yr_mean_citedness": round(summary.get("2yr_mean_citedness", 0), 2),
                    "institucion": inst_name,
                    "campo_principal": campo,
                    "pais": "CL",
                }
                all_authors.append(author_data)
                cs_count += 1

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            total = meta.get("count", 0)
            page += 1

            if page % 20 == 0:
                print(f"  Pag {page}: {len(all_authors)} CS / {page*200} procesados de {total}")

            sleep(0.05)

        except requests.RequestException as e:
            print(f"  Error pag {page}: {e}")
            sleep(2)
            continue

    print(f"\nTotal descargado: {page * 200} autores")
    print(f"Ciencias Sociales: {len(all_authors)}")
    return all_authors


def main():
    """Función principal."""
    print("=" * 60)
    print("EXTRACCION OPENALEX - CIENCIAS SOCIALES CHILE")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    authors = get_authors_chile()

    if not authors:
        print("No se encontraron autores.")
        return None

    df = pd.DataFrame(authors)
    df = df.drop_duplicates(subset=["openalex_id"])
    df = df.sort_values("h_index", ascending=False)

    # Guardar
    fecha = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"investigadores_openalex_{fecha}.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print("=" * 60)
    print(f"Total investigadores CS: {len(df)}")
    print(f"h-index >= 1: {len(df[df['h_index'] >= 1])}")
    print(f"h-index >= 5: {len(df[df['h_index'] >= 5])}")
    print(f"Archivo: {output_file}")

    print(f"\nPor campo:")
    print(df["campo_principal"].value_counts().head(10))

    print(f"\nPor institucion (top 10):")
    print(df["institucion"].value_counts().head(10))

    print(f"\nTop 10 h-index:")
    for _, r in df.head(10).iterrows():
        print(f"  {r['nombre'][:40]:40} h={r['h_index']:2} citas={r['cited_by_count']:,}")

    return df


if __name__ == "__main__":
    main()
