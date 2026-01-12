"""
Genera el ranking desde un CSV con datos ya recopilados.

Uso:
    python src/ranking_desde_csv.py data/seed/plantilla_datos.csv
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

def generar_ranking(input_file: str):
    """Genera ranking desde CSV con datos."""

    # Leer datos
    df = pd.read_csv(input_file)

    # Filtrar filas con datos (h_index no vacío)
    df = df[df['h_index'].notna() & (df['h_index'] != '')]
    df['h_index'] = pd.to_numeric(df['h_index'], errors='coerce').fillna(0).astype(int)
    df['citations'] = pd.to_numeric(df['citations'], errors='coerce').fillna(0).astype(int)
    df['i10_index'] = pd.to_numeric(df['i10_index'], errors='coerce').fillna(0).astype(int)

    if len(df) == 0:
        print("No hay datos válidos en el archivo.")
        print("\nPasos:")
        print("1. Abre plantilla_datos.csv en Excel")
        print("2. Haz clic en cada URL para ver el perfil")
        print("3. Copia los datos (nombre, h-index, citas, etc.)")
        print("4. Guarda el archivo y ejecuta este script de nuevo")
        return None

    # Ordenar por h-index y citas
    ranking = df.sort_values(
        by=['h_index', 'citations'],
        ascending=[False, False]
    ).reset_index(drop=True)

    # Agregar posición
    ranking.insert(0, 'rank', range(1, len(ranking) + 1))

    # Guardar
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # CSV
    csv_file = output_dir / f"ranking_ciencias_sociales_{timestamp}.csv"
    ranking.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"CSV guardado: {csv_file}")

    # Excel
    xlsx_file = output_dir / f"ranking_ciencias_sociales_{timestamp}.xlsx"
    ranking.to_excel(xlsx_file, index=False)
    print(f"Excel guardado: {xlsx_file}")

    # Mostrar ranking
    print("\n" + "="*60)
    print("RANKING CIENCIAS SOCIALES CHILE")
    print("="*60)
    print(f"\nTotal: {len(ranking)} investigadores\n")

    cols_display = ['rank', 'nombre', 'h_index', 'citations', 'afiliacion']
    cols_available = [c for c in cols_display if c in ranking.columns]

    print(ranking[cols_available].to_string(index=False))

    # Estadísticas
    print("\n" + "-"*40)
    print("ESTADÍSTICAS")
    print("-"*40)
    print(f"H-index promedio: {ranking['h_index'].mean():.1f}")
    print(f"H-index mediana:  {ranking['h_index'].median():.0f}")
    print(f"H-index máximo:   {ranking['h_index'].max()}")
    print(f"Citas totales:    {ranking['citations'].sum():,}")

    return ranking


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "data/seed/plantilla_datos.csv"

    generar_ranking(input_file)
