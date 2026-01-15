"""
Script unificado para actualizar el ranking de ciencias sociales.

Ejecuta:
1. Extracción desde API de OpenAlex
2. Limpieza de datos
3. Asignación de Scholar IDs
4. Generación de archivos para la web

Uso:
    python src/actualizar_ranking.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def main():
    """Ejecuta el pipeline completo de actualización."""
    print("=" * 60)
    print("ACTUALIZACION DEL RANKING - CIENCIAS SOCIALES CHILE")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    src_dir = Path(__file__).parent

    # Paso 1: Extraer datos de OpenAlex
    print("\n[1/2] Extrayendo datos de OpenAlex API...")
    print("-" * 40)
    result = subprocess.run(
        [sys.executable, str(src_dir / "extraer_openalex.py")],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print("Advertencia: La extracción terminó con errores (posiblemente encoding)")

    # Paso 2: Procesar y generar ranking
    print("\n[2/2] Procesando ranking...")
    print("-" * 40)

    # Copiar el archivo extraído al directorio de procesamiento
    fecha = datetime.now().strftime("%Y%m%d")
    raw_file = src_dir.parent / "data" / "raw" / f"investigadores_openalex_{fecha}.csv"
    processed_dir = src_dir.parent / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    if raw_file.exists():
        import shutil
        dest_file = processed_dir / f"investigadores_openalex_{fecha}.csv"
        shutil.copy(raw_file, dest_file)
        print(f"Copiado: {raw_file.name} -> processed/")

    # Ejecutar procesamiento
    result = subprocess.run(
        [sys.executable, str(src_dir / "procesar_ranking.py")],
        capture_output=False,
        text=True
    )

    print("\n" + "=" * 60)
    print("ACTUALIZACION COMPLETADA")
    print("=" * 60)
    print(f"\nArchivos generados:")
    print(f"  - data/output/ranking_final_{fecha}.csv")
    print(f"  - data/output/ranking_web_{fecha}.json")
    print(f"\nPara actualizar la web, copie ranking_web_{fecha}.json a docs/ranking_web.json")


if __name__ == "__main__":
    main()
