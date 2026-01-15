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
H_INDEX_MINIMO = 1  # Solo investigadores con h-index >= 1
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

# Scholar IDs conocidos (verificados manualmente via Google Search)
SCHOLAR_IDS_CONOCIDOS = {
    # Top investigadores por h-index
    "David Altman": "oZGkFZoAAAAJ",
    "Darío Páez": "KVva2AIAAAAJ",
    "Francisca Fariña Rivera": "4JpTKi0AAAAJ",
    "Salvador Chacón Moscoso": "LeQUGDIAAAAJ",
    "Miguel Alfaro": "0zwnLpAAAAAJ",
    "Juan-Carlos Ferrer": "1N8BNr8AAAAJ",
    "Juan‐Carlos Ferrer": "1N8BNr8AAAAJ",
    "Cristóbal Rovira Kaltwasser": "RdXwR1EAAAAJ",
    "Alejandro Micco": "BUc-k1MAAAAJ",
    "Claudio E. Montenegro": "qO3kU6UAAAAJ",
    "Patricio Navia": "IBcs-ZwAAAAJ",
    "José Joaquín Brunner": "TX3te0QAAAAJ",
    "Alejandra Mizala": "zmkA7uwAAAAJ",
    "Daniel Chernilo": "QASCP9kAAAAJ",
    "Vicente Sisto": "g_QWxVAAAAAJ",
    "Paula Ascorra": "YVBJgLwAAAAJ",
    "Aldo Mascareño": "7H4k-70AAAAJ",
    "Mahía Saracostti": "pWZjC4AAAAAJ",
    "Juan Carlos Castillo": "CPJ0qfQAAAAJ",
    "Nicolás M. Somma": "yyr6ge0AAAAJ",
    "Cristóbal Villalobos": "PM99kxMAAAAJ",
    "Mauricio Morales": "BPVbhToAAAAJ",
    "Javier Núñez": "2a__7xUAAAAJ",
    "Aldo Madariaga": "n0UQqa4AAAAJ",
    "Jenny Assaél": "4bK5XUQAAAAJ",
    "Cristián Parker Gumucio": "8kIJIa4AAAAJ",
    "Cynthia Duk": "bxBuLfMAAAAJ",
    "Nicole Jenne": "HaX6qs4AAAAJ",
    "Kathya Araujo": "nukHXv0AAAAJ",
    "Antonio Stecher": "rFUqIdsAAAAJ",
    "Felipe Link": "9cxoZ8MAAAAJ",
    "Cristián Cox": "9b8DoS8AAAAJ",
    "Anahí Urquiza": "eU41CdMAAAAJ",
    "Luis Quezada": "rVVdDTMAAAAJ",
    "Felipe González": "dwxwyqwAAAAJ",
    "Elizabeth Lira": "VDEOCBgAAAAJ",
    "María Luisa Méndez": "DCQO_AgAAAAJ",
    "Antoine Maillet": "Y4q4OfoAAAAJ",
    "Rossana Castiglioni": "gkHNPiwAAAAJ",
    "Modesto Gayo": "k-2PLOsAAAAJ",
    "Alejandra Falabella": "G-JkMjwAAAAJ",
    "Vicente Espinoza": "L8DtBnQAAAAJ",
    "Caterine Galaz Valderrama": "iBW6M4gAAAAJ",
    "Mauricio López": "nWzmqycAAAAJ",
    "Esteban Puentes": "zhJ_wAUAAAAJ",
    "José Tessada": "i3T7_ocAAAAJ",
    "Marcela Aracena": "kT-y4RgAAAAJ",
    "Nicolás Didier": "rDyVn7QAAAAJ",
    "Eduardo Restrepo": "G51Wqn0AAAAJ",
    "Héctor López-Ospina": "e_0UrIMAAAAJ",
    "Iskra Pávez Soto": "PZWoraMAAAAJ",
    "Jaime Miranda": "wd06koYAAAAJ",
    "Matías Berthelon": "8nUNv-QAAAAJ",
    "Pedro Palominos": "Q81kXv4AAAAJ",
    "Alejandro Corvalán": "KiGpYt4AAAAJ",
    "Ricardo A. Ayala": "p4WjxQoAAAAJ",
    "Juan Diego García-Castro": "o_ReskMAAAAJ",
    "Juan Diego García‐Castro": "o_ReskMAAAAJ",
    "María Cristina Riff": "V9BgXgMAAAAJ",
    "Héctor Opazo Carvajal": "gdu2HV8AAAAJ",
    "Luis Maldonado": "jw0bvrYAAAAJ",
    "Verónica Gómez Urrutia": "HEFa7TgAAAAJ",
    "Carlos Rodríguez Garcés": "PQix8vkAAAAJ",
    "Carmen Gloria Núñez": "3DJ2obYAAAAJ",
    "Valeria Herrera Fernández": "KpR_9ssAAAAJ",
    "Alexandre Janiak": "ZUI_nRsAAAAJ",
    "Francisco Pino": "gglIsfcAAAAJ",
    "Martina Yopo Díaz": "d_EShyMAAAAJ",
    "Manuela García Quiroga": "YphStrYAAAAJ",
    "Carmen Le Foulon": "wRPMNvUAAAAJ",
    "Carlos Villalobos Barría": "ys7_WJsAAAAJ",
    "Alexander Panez Pinto": "j0jLMmUAAAAJ",
    "Francisco Soto": "bQFVXJIAAAAJ",
    "Felipe Agüero": "JSPWdfYAAAAJ",
    "Juan Carlos Peña Axt": "M1HHaLAAAAAJ",
    "Lyonel Laulié": "YrUlat4AAAAJ",
    "María Emilia Tijoux": "w4yfwDwAAAAJ",
    "Macarena Trujillo Cristoffanini": "WUBNh6cAAAAJ",
    "Gianinna Muñoz Arce": "69DPxiIAAAAJ",
    "Cristóbal Villalobos Dintrans": "2Luja0YAAAAJ",
    "Alicia Salomone": "dt0d5aYAAAAJ",
    "Jeanne W. Simon": "_mHLvikAAAAJ",
    "Pablo Camus": "__gOnGQAAAAJ",
    "Taly Reininger": "s-2CFoYAAAAJ",
    "Rodrigo Medel Sierralta": "nYgItkMAAAAJ",
    "Rodrigo M. Medel": "nYgItkMAAAAJ",
    "María Teresa Rojas Fabris": "FJPZ-FMAAAAJ",
    "Pamela Soto García": "LHY0duUAAAAJ",
    "Carlos Durán Migliardi": "B4nKyykAAAAJ",
    "Lorena Pérez-Roa": "6fbnHhQAAAAJ",
    "Nelson Arellano Escudero": "feRyeYcAAAAJ",
    "Rodrigo A. Asún": "airlFmQAAAAJ",
    "Rodrigo Asún": "airlFmQAAAAJ",
    "Camila Moyano Dávila": "Z_5xEkIAAAAJ",
    "Claudia Zúñiga": "PrpjOXQAAAAJ",
    "Javiera Cienfuegos Illanes": "VZBKOLsAAAAJ",
    "Cristián Bellei": "UeodjIAAAAAJ",
    "Cristian Bellei": "UeodjIAAAAAJ",
    "Mauro Basaure": "JPWSU2wAAAAJ",
    "Carolina Stefoni": "p86gQo0AAAAJ",
    "Silvia Lamadrid Alvarez": "t6B1cxEAAAAJ",
    "Silvia Lamadrid": "t6B1cxEAAAAJ",
    "Javier Ruiz-Tagle": "os329F8AAAAJ",
    "Oscar Landerretche": "W6oI2LsAAAAJ",
    "Gonzalo Martner": "7OcQ0PoAAAAJ",
    "Eduardo Engel": "PWLh77oAAAAJ",
    "Pablo Marshall": "HzOFxjoAAAAJ",
    "Pablo Geraldo Bastías": "JrrvH-oAAAAJ",
    "Andrea Riedemann": "KnrUWzEAAAAJ",
    "Pablo Pérez Ahumada": "I-bh4HoAAAAJ",
    "Kathya Araujo": "nukHXv0AAAAJ",
    "Fernando Atria": "InrV7oEAAAAJ",
    "Martín Tironi": "_CTu_voAAAAJ",
    "Tomás Ariztía": "FpyJ96kAAAAJ",
    "Eugenio Tironi": "8g7eKDcAAAAJ",
    "Claudia Sanhueza": "kuProYAAAAAJ",
    "Dante Contreras": "BUc-k1MAAAAJ",
    "Carlos Huneeus": "Kq4dWnoAAAAJ",
    "Juan Pablo Luna": "IgwSc8oAAAAJ",
    "Florencia Torche": "HjhELVoAAAAJ",
    "Rodrigo Valdés": "vfhPXR4AAAAJ",
    "Andrea Repetto": "zmkA7uwAAAAJ",
    "Sergio Urzúa": "UGlSd5kAAAAJ",
    "Francisco A. Gallego": "l7Q0SrUAAAAJ",
    "Francisco Gallego": "l7Q0SrUAAAAJ",
    "José De Gregorio": "SJUEA8uk4iYC",
    "Claudia Mora": "psDDX5MAAAAJ",
    "Juan Carlos Oyanedel": "UsXLvsEAAAAJ",
    "Ernesto López-Morales": "5w40_sYAAAAJ",
    "Ernesto López Morales": "5w40_sYAAAAJ",
    "Luis Garrido-Vergara": "DlO0jXVS4FIC",
    "Luis Garrido Vergara": "DlO0jXVS4FIC",
    "José Weinstein": "XrZEaYcAAAAJ",
    "Gonzalo Muñoz Stuardo": "rC7E0W8AAAAJ",
    "Sergio Martinic": "P3vUyD8AAAAJ",
    "Osvaldo Sunkel": "GEuJF0cAAAAJ",
    "Aldo Mascareño": "7H4k-70AAAAJ",
    "Arturo Arriagada": "TzPYdWsAAAAJ",
    "José Joaquín Brunner": "TX3te0QAAAAJ",
    "Pedro Güell": "KaRIsccAAAAJ",
    # Otros investigadores
    "Matías Bargsted": "0oYjLYEAAAAJ",
    "Alfredo Joignant": "C6i7344AAAAJ",
    "Emmanuelle Barozet": "NLiNCD0AAAAJ",
    "Émmanuelle Barozet": "NLiNCD0AAAAJ",
    "Sergio Toro": "F7Dguu4AAAAJ",
    "Ricardo Gamboa": "nOBjxWUAAAAJ",
    "Ricardo Gamboa Valenzuela": "nOBjxWUAAAAJ",
    "Claudio Fuentes": "ckIjzZQAAAAJ",
    "Magdalena Saldaña": "UknWOrEAAAAJ",
    "Catherine Reyes-Housholder": "8WfwsloAAAAJ",
    "Octavio Avendaño": "gj1MwGwAAAAJ",
    "Lisa Zanotti": "JD_X4KYAAAAJ",
    "Carla Fardella": "h9ECWD4AAAAJ",
    "Manuel Canales Cerón": "VUBBRpoAAAAJ",
    "Manuel Canales": "VUBBRpoAAAAJ",
    # Nuevos IDs agregados (búsqueda 2026-01-14)
    "F. Daniel Hidalgo": "r-UN7tMAAAAJ",
    "Marcelo Arnold-Cathalifaud": "0eZSQEkAAAAJ",
    "Marcelo Arnold": "0eZSQEkAAAAJ",
    "Rodrigo Cordero": "22ynv5cAAAAJ",
    "Jorge Atria Curi": "6lYgX_0AAAAJ",
    "Jorge Atria": "6lYgX_0AAAAJ",
    "Antonio Elizalde": "egxxLU0AAAAJ",
    "Matias López": "_y8jWtcAAAAJ",
    "Verónica Gubbins Foxley": "tW__CQYAAAAJ",
    "Verónica Gubbins": "tW__CQYAAAAJ",
    "Felipe Torres Torres": "8bXFNDIAAAAJ",
    "Felipe Torres": "8bXFNDIAAAAJ",
    "Francisca Dussaillant": "6XHFLYQAAAAJ",
    "Óscar Mac-Clure": "XmHLcYkAAAAJ",
    "Oscar Mac-Clure": "XmHLcYkAAAAJ",
    "Carlos Calvo Muñoz": "Sc7FKWEAAAAJ",
    "Carlos Calvo": "Sc7FKWEAAAAJ",
    "Álvaro Besoaín Saldaña": "zt_Pe8wAAAAJ",
    "Alvaro Besoain Saldaña": "zt_Pe8wAAAAJ",
    "Facundo Sepúlveda": "8yeHoG8AAAAJ",
    "Facundo Sepulveda": "8yeHoG8AAAAJ",
    "César A. Cisneros Puebla": "k7EIK5UAAAAJ",
    "César Cisneros Puebla": "k7EIK5UAAAAJ",
    "Daina Bellido de Luna": "LqFe6MQAAAAJ",
    "Juan Pablo Venables": "OQM9rGQAAAAJ",
    "Juan Pablo Paredes P": "keKcSfsAAAAJ",
    "Juan Pablo Paredes": "keKcSfsAAAAJ",
    "Juan Pablo Pinilla": "HsctFRkAAAAJ",
    "Kenneth Bunker": "kFHaW6wAAAAJ",
    "Álvaro V. Ramírez-Alujas": "MMCj-VQAAAAJ",
    "Álvaro Ramírez-Alujas": "MMCj-VQAAAAJ",
    "Daniel Miranda": "vdF2kZcAAAAJ",
    "Rodrigo Mardones": "5cAowpkAAAAJ",
}


def cargar_datos(filepath: Path) -> pd.DataFrame:
    """Carga el CSV de OpenAlex y normaliza nombres de columnas."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")

    # Normalizar nombres de columnas para compatibilidad entre formatos
    column_mapping = {
        "cited_by_count": "citas",
        "pais": "pais_institucion",
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Asegurar que existe columna 'citas'
    if "citas" not in df.columns and "cited_by_count" not in df.columns:
        df["citas"] = 0

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

    # 4. Solo país Chile (compatible con ambos formatos)
    if "pais_institucion" in df.columns:
        df = df[df["pais_institucion"] == "CL"]
    elif "pais" in df.columns:
        df = df[df["pais"] == "CL"]
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
            "scholar_id": row.get("scholar_id", ""),
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

    # Buscar archivo más reciente de OpenAlex (en output/ o raw/)
    archivos = list(OUTPUT_DIR.glob("investigadores_openalex_*.csv"))
    raw_dir = OUTPUT_DIR.parent / "raw"
    if raw_dir.exists():
        archivos.extend(list(raw_dir.glob("investigadores_openalex_*.csv")))
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
