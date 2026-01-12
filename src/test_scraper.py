"""
Script de prueba para verificar que el scraper funciona correctamente.
Ejecuta una búsqueda pequeña para validar la configuración.

Uso:
    python src/test_scraper.py
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from scraper import ScholarScraper
import json


def test_single_author():
    """Prueba obtener un autor específico por ID."""
    print("=" * 50)
    print("TEST 1: Obtener autor por ID")
    print("=" * 50)

    scraper = ScholarScraper(delay_range=(1, 2))

    # Bastián González-Bustamante como ejemplo
    author = scraper.get_author_by_id("UknWOrEAAAAJ")

    if author:
        print(f"Nombre: {author['name']}")
        print(f"Afiliación: {author['affiliation']}")
        print(f"H-index: {author['h_index']}")
        print(f"Citas: {author['citations']}")
        print(f"Intereses: {', '.join(author['interests'][:5])}")
        print("TEST PASADO")
        return True
    else:
        print("ERROR: No se pudo obtener el autor")
        return False


def test_search_by_discipline():
    """Prueba búsqueda por disciplina."""
    print("\n" + "=" * 50)
    print("TEST 2: Buscar por disciplina + Chile")
    print("=" * 50)

    scraper = ScholarScraper(delay_range=(2, 3))

    authors = scraper.search_by_keyword_and_location(
        keyword="sociología",
        location="Chile",
        max_results=5
    )

    print(f"Encontrados: {len(authors)} autores")

    for author in authors:
        print(f"  - {author['name']} (H: {author['h_index']})")

    if len(authors) > 0:
        print("TEST PASADO")
        return True
    else:
        print("ADVERTENCIA: No se encontraron autores (puede ser rate limiting)")
        return False


def test_search_by_university():
    """Prueba búsqueda por universidad."""
    print("\n" + "=" * 50)
    print("TEST 3: Buscar por universidad")
    print("=" * 50)

    scraper = ScholarScraper(delay_range=(2, 3))

    authors = scraper.search_by_affiliation(
        affiliation="Universidad de Chile",
        max_results=5
    )

    print(f"Encontrados: {len(authors)} autores")

    for author in authors:
        print(f"  - {author['name']}")
        print(f"    {author['affiliation'][:60]}")

    if len(authors) > 0:
        print("TEST PASADO")
        return True
    else:
        print("ADVERTENCIA: No se encontraron autores")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "#" * 50)
    print("# PRUEBAS DEL SCRAPER DE GOOGLE SCHOLAR")
    print("#" * 50 + "\n")

    results = []

    try:
        results.append(("Obtener autor por ID", test_single_author()))
    except Exception as e:
        print(f"ERROR en test 1: {e}")
        results.append(("Obtener autor por ID", False))

    try:
        results.append(("Buscar por disciplina", test_search_by_discipline()))
    except Exception as e:
        print(f"ERROR en test 2: {e}")
        results.append(("Buscar por disciplina", False))

    try:
        results.append(("Buscar por universidad", test_search_by_university()))
    except Exception as e:
        print(f"ERROR en test 3: {e}")
        results.append(("Buscar por universidad", False))

    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN DE PRUEBAS")
    print("=" * 50)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "PASADO" if result else "FALLIDO"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} pruebas pasadas")

    if passed == total:
        print("\nEl scraper está funcionando correctamente.")
        print("Puedes ejecutar: python src/main.py --test")
    else:
        print("\nAlgunas pruebas fallaron. Verifica tu conexión a internet")
        print("y que no estés siendo bloqueado por Google Scholar.")


if __name__ == "__main__":
    main()
