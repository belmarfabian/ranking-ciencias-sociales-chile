"""
Procesa y limpia los datos de OpenAlex para generar el ranking final.

1. Limpia errores de afiliación
2. Filtra por h-index mínimo
3. Busca scholar_id de Google Scholar
4. Genera archivo para la página web
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import json
import re
from time import sleep

# Configuración
H_INDEX_MINIMO = 2  # Solo investigadores con h-index >= 2
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"

# Investigadores a excluir (errores de OpenAlex o no son chilenos)
EXCLUIR_NOMBRES = [
    "Arend Lijphart",  # Politólogo holandés/estadounidense, no chileno
    "Alain Touraine",  # Sociólogo francés
    "Max Weber",  # Error obvio
    "Harold H. Joachim",  # Filósofo británico histórico
    "Marisa Bucheli",  # Uruguaya
    "Andrea Vigorito",  # Uruguaya
    "Adolfo Garcé",  # Uruguayo
    "Liliana de Riz",  # Argentina
    "Guillermo Durán",  # Argentino
    "Ricardo Paes de Barros",  # Brasileño
    "Travis Gagie",  # Canadiense
    "Diana Fletschner",  # No chilena
    "Diana Krüger",  # Alemana/Kenya
    "José Gabriel Palma",  # Reino Unido (aunque chileno de origen, no está en Chile)
    "Fernando Gutiérrez Hidalgo",  # España
    "Pablo A. Miranda",  # India
    "W.G.P. Kumari",  # Australia
    "Stefano Novellani",  # Italiano
    "J. Arzúa",  # España
    "Fernando Alonso",  # España
    "Pablo González",  # España (Instituto Santiago pero no es Chile)
    "Carola Blázquez",  # Francia
    "Antônio Galvão Novaes",  # Error de afiliación
    "Juan M. Corchado",  # Argentina, Computer Science
]

# Afiliaciones a excluir (no son instituciones chilenas reales)
EXCLUIR_AFILIACIONES = [
    "Gobierno de Chile",  # Error de OpenAlex
    "Partnership for Economic Policy",  # Kenya
    "World Bank Group",  # Internacional
    "World Health Organization",  # Internacional
    "University of Cambridge",  # UK
    "Vellore Institute of Technology",  # India
    "University of Wollongong",  # Australia
    "McGill University",  # Canadá
    "Dalhousie University",  # Canadá
    "IFP Énergies nouvelles",  # Francia
    "Universitat de Barcelona",  # España
    "Universidad Complutense de Madrid",  # España
    "Universidad de Buenos Aires",  # Argentina
    "Universidade de Vigo",  # España
    "Hospital Universitario de Canarias",  # España
    "Universidad de la República",  # Uruguay (no confundir con La República Chile)
]

# Campos que NO son ciencias sociales (filtro adicional)
CAMPOS_EXCLUIR = [
    "Computer Science",
    "Engineering",
    "Mathematics",
    "Physics and Astronomy",
    "Environmental Science",
    "Medicine",
    "Neuroscience",
]

# Scholar IDs conocidos (de nuestro ranking anterior + búsqueda manual)
SCHOLAR_IDS_CONOCIDOS = {
    "David Altman": "oZGkFZoAAAAJ",
    "Cristóbal Rovira Kaltwasser": "RdXwR1EAAAAJ",
    "Patricio Navia": "IBcs-ZwAAAAJ",
    "Daniel Chernilo": "sHV_7OoAAAAJ",  # Verificar
    "Juan Carlos Castillo": "yyr6ge0AAAAJ",  # Verificar
    "Nicolás M. Somma": "yyr6ge0AAAAJ",
    "Mauricio Morales": "BPVbhToAAAAJ",
    "Matías Bargsted": "5q8wMVcAAAAJ",  # Verificar
    "Alfredo Joignant": "5q8wMVcAAAAJ",
    "Emmanuelle Barozet": "NLiNCD0AAAAJ",
    "Émmanuelle Barozet": "NLiNCD0AAAAJ",
    "Sergio Toro": "F7Dguu4AAAAJ",
    "Ricardo Gamboa": "ckIjzZQAAAAJ",  # Verificar
    "Magdalena Saldaña": "UknWOrEAAAAJ",  # Verificar
    "Alejandra Mizala": "zmkA7uwAAAAJ",  # Verificar
    "Claudio Sapelli": "PWLh77oAAAAJ",  # Verificar
    "Nicole Jenne": "HaX6qs4AAAAJ",  # Verificar
    "Catherine Reyes-Housholder": "gkHNPiwAAAAJ",  # Verificar
    "Octavio Avendaño": "gj1MwGwAAAAJ",  # Verificar
    "Lisa Zanotti": "JD_X4KYAAAAJ",  # Verificar
    "Alejandro Micco": "BUc-k1MAAAAJ",  # Verificar
    "Claudio E. Montenegro": "PWLh77oAAAAJ",  # Verificar
}


def cargar_datos(filepath: Path) -> pd.DataFrame:
    """Carga el CSV de OpenAlex."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    print(f"Cargados {len(df)} investigadores")
    return df


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia los datos eliminando errores y no chilenos.
    """
    n_inicial = len(df)

    # 1. Eliminar por nombre
    df = df[~df["nombre"].isin(EXCLUIR_NOMBRES)]
    print(f"  Después de excluir nombres: {len(df)}")

    # 2. Eliminar por afiliación
    df = df[~df["institucion"].isin(EXCLUIR_AFILIACIONES)]
    print(f"  Después de excluir afiliaciones: {len(df)}")

    # 3. Eliminar campos no sociales (doble check)
    df = df[~df["campo_principal"].isin(CAMPOS_EXCLUIR)]
    print(f"  Después de excluir campos: {len(df)}")

    # 4. Solo país Chile
    df = df[df["pais_institucion"] == "CL"]
    print(f"  Después de filtrar país CL: {len(df)}")

    print(f"Eliminados {n_inicial - len(df)} registros en limpieza")
    return df


def filtrar_por_hindex(df: pd.DataFrame, minimo: int = H_INDEX_MINIMO) -> pd.DataFrame:
    """Filtra investigadores con h-index >= minimo."""
    df = df[df["h_index"] >= minimo]
    print(f"Después de filtrar h-index >= {minimo}: {len(df)}")
    return df


def buscar_scholar_id(nombre: str, afiliacion: str) -> str:
    """
    Intenta buscar el scholar_id usando SerpAPI o búsqueda manual.
    Por ahora usa el diccionario de IDs conocidos.
    """
    # Primero buscar en IDs conocidos
    if nombre in SCHOLAR_IDS_CONOCIDOS:
        return SCHOLAR_IDS_CONOCIDOS[nombre]

    # Normalizar nombre para búsqueda
    nombre_normalizado = nombre.replace("‐", "-").replace("–", "-")
    if nombre_normalizado in SCHOLAR_IDS_CONOCIDOS:
        return SCHOLAR_IDS_CONOCIDOS[nombre_normalizado]

    # TODO: Implementar búsqueda con SerpAPI si se tiene API key
    # Por ahora retornar vacío
    return ""


def agregar_scholar_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega scholar_id a los investigadores."""
    df["scholar_id"] = df.apply(
        lambda row: buscar_scholar_id(row["nombre"], row["institucion"]),
        axis=1
    )

    con_id = (df["scholar_id"] != "").sum()
    print(f"Investigadores con scholar_id: {con_id}/{len(df)}")
    return df


def clasificar_disciplina(row) -> str:
    """Clasifica la disciplina basándose en el campo y topics."""
    campo = row.get("campo_principal", "")
    topics = row.get("topics", "").lower()

    # Ciencia Política
    if any(x in topics for x in ["political", "electoral", "democracy", "populism",
                                   "governance", "international relations"]):
        return "Ciencia Política"

    # Sociología
    if any(x in topics for x in ["sociolog", "social stratification", "inequality",
                                   "social movement", "cultural"]):
        return "Sociología"

    # Economía
    if campo == "Economics, Econometrics and Finance" or \
       any(x in topics for x in ["economic", "labor market", "fiscal", "trade"]):
        return "Economía"

    # Psicología
    if campo == "Psychology" or "psycholog" in topics:
        return "Psicología"

    # Educación
    if any(x in topics for x in ["education", "school", "teacher"]):
        return "Educación"

    # Comunicación
    if any(x in topics for x in ["media", "communication", "journalism"]):
        return "Comunicación"

    # Default basado en campo
    if campo == "Social Sciences":
        return "Ciencias Sociales"
    if campo == "Arts and Humanities":
        return "Humanidades"
    if "Business" in campo:
        return "Administración"

    return "Ciencias Sociales"


def agregar_disciplina(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega clasificación de disciplina."""
    df["disciplina"] = df.apply(clasificar_disciplina, axis=1)

    print("\nDistribución por disciplina:")
    print(df["disciplina"].value_counts())
    return df


def normalizar_institucion(institucion: str) -> str:
    """Normaliza nombres de instituciones."""
    mapeo = {
        "Pontificia Universidad Católica de Chile": "PUC Chile",
        "University of Chile": "U. Chile",
        "Universidad de Santiago de Chile": "USACH",
        "Universidad Diego Portales": "UDP",
        "Adolfo Ibáñez University": "UAI",
        "University of Talca": "U. Talca",
        "Universidad Mayor": "U. Mayor",
        "Pontificia Universidad Católica de Valparaíso": "PUCV",
        "Federico Santa María Technical University": "USM",
        "Austral University of Chile": "UACh",
        "University of Valparaíso": "UV",
        "University of Concepción": "UdeC",
        "Universidad de Los Andes, Chile": "U. Andes",
        "Centro de Estudios Científicos": "CECS",
        "Centro de Recursos Educativos Avanzados": "CREA",
        "Universidad Andrés Bello": "UNAB",
        "Universidad del Desarrollo": "UDD",
        "Universidad Alberto Hurtado": "UAH",
        "Finis Terrae University": "U. Finis Terrae",
        "San Sebastián University": "USS",
        "Universidad La República": "U. La República",
        "Universidad de La Frontera": "UFRO",
        "University of Bío-Bío": "UBB",
        "Millennium Science Initiative": "ICM",
        "Data Observatory Foundation": "Data Observatory",
        "Inria Chile": "Inria Chile",
    }

    return mapeo.get(institucion, institucion)


def generar_json_web(df: pd.DataFrame, output_path: Path):
    """Genera JSON para la página web."""

    # Preparar datos para JavaScript
    investigadores = []
    for _, row in df.iterrows():
        inv = {
            "id": row.get("scholar_id", "") or row.get("openalex_id", ""),
            "openalex_id": row.get("openalex_id", ""),
            "orcid": row.get("orcid", ""),
            "name": row["nombre"],
            "affiliation": normalizar_institucion(row["institucion"]),
            "d1": abreviar_disciplina(row["disciplina"]),
            "d2": "",
            "topics": extraer_topics_cortos(row.get("topics", "")),
            "hindex": int(row["h_index"]),
            "citations": int(row["citas"]),
            "works": int(row.get("trabajos", 0)),
        }
        investigadores.append(inv)

    # Guardar JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(investigadores, f, ensure_ascii=False, indent=2)

    print(f"\nGenerado JSON: {output_path}")
    return investigadores


def abreviar_disciplina(disciplina: str) -> str:
    """Abrevia nombre de disciplina para la web."""
    mapeo = {
        "Ciencia Política": "C.Pol",
        "Sociología": "Soc",
        "Economía": "Econ",
        "Psicología": "Psic",
        "Educación": "Educ",
        "Comunicación": "Com",
        "Humanidades": "Hum",
        "Administración": "Adm",
        "Ciencias Sociales": "CS",
    }
    return mapeo.get(disciplina, disciplina[:4])


def extraer_topics_cortos(topics_str: str, max_topics: int = 3) -> str:
    """Extrae y acorta los topics para mostrar."""
    if not topics_str:
        return ""

    topics = topics_str.split(";")[:max_topics]

    # Limpiar y acortar
    topics_limpios = []
    for t in topics:
        t = t.strip()
        # Quitar palabras comunes
        t = t.replace(" and ", ", ").replace(" in ", " ")
        # Acortar si es muy largo
        if len(t) > 40:
            t = t[:37] + "..."
        topics_limpios.append(t)

    return "; ".join(topics_limpios)


def guardar_csv_final(df: pd.DataFrame, output_path: Path):
    """Guarda CSV final limpio."""

    # Seleccionar columnas relevantes
    columnas = [
        "ranking", "nombre", "institucion", "disciplina",
        "h_index", "citas", "trabajos",
        "scholar_id", "openalex_id", "orcid", "topics"
    ]

    # Solo columnas que existen
    columnas = [c for c in columnas if c in df.columns]

    df_final = df[columnas].copy()
    df_final.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Guardado CSV final: {output_path}")


def main():
    print("="*60)
    print("PROCESAMIENTO DE RANKING - CIENCIAS SOCIALES CHILE")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Buscar archivo más reciente de OpenAlex
    archivos = list(OUTPUT_DIR.glob("investigadores_openalex_*.csv"))
    if not archivos:
        print("ERROR: No se encontró archivo de OpenAlex")
        return

    archivo_mas_reciente = max(archivos, key=lambda x: x.stat().st_mtime)
    print(f"Archivo fuente: {archivo_mas_reciente.name}\n")

    # Cargar datos
    df = cargar_datos(archivo_mas_reciente)

    # Limpiar
    print("\n" + "="*50)
    print("LIMPIEZA DE DATOS")
    print("="*50)
    df = limpiar_datos(df)

    # Filtrar por h-index
    print("\n" + "="*50)
    print("FILTRO POR H-INDEX")
    print("="*50)
    df = filtrar_por_hindex(df, H_INDEX_MINIMO)

    # Clasificar disciplina
    print("\n" + "="*50)
    print("CLASIFICACIÓN DE DISCIPLINAS")
    print("="*50)
    df = agregar_disciplina(df)

    # Agregar scholar IDs
    print("\n" + "="*50)
    print("BÚSQUEDA DE SCHOLAR IDs")
    print("="*50)
    df = agregar_scholar_ids(df)

    # Reordenar por h-index y asignar ranking
    df = df.sort_values("h_index", ascending=False).reset_index(drop=True)
    df["ranking"] = range(1, len(df) + 1)

    # Guardar resultados
    print("\n" + "="*50)
    print("GUARDANDO RESULTADOS")
    print("="*50)

    fecha = datetime.now().strftime("%Y%m%d")

    # CSV final
    csv_path = OUTPUT_DIR / f"ranking_final_{fecha}.csv"
    guardar_csv_final(df, csv_path)

    # JSON para web
    json_path = OUTPUT_DIR / f"ranking_web_{fecha}.json"
    investigadores = generar_json_web(df, json_path)

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"Total investigadores: {len(df)}")
    print(f"H-index promedio: {df['h_index'].mean():.1f}")
    print(f"H-index máximo: {df['h_index'].max()}")
    print(f"Citas totales: {df['citas'].sum():,}")

    print("\nTop 15 por H-index:")
    top15 = df.head(15)[["ranking", "nombre", "institucion", "disciplina", "h_index", "citas"]]
    print(top15.to_string(index=False))

    return df, investigadores


if __name__ == "__main__":
    main()
