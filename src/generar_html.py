"""
Genera la página HTML del ranking desde el CSV procesado.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import json

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def cargar_datos():
    """Carga el CSV más reciente."""
    archivos = list(OUTPUT_DIR.glob("ranking_final_*.csv"))
    if not archivos:
        raise FileNotFoundError("No se encontró archivo ranking_final_*.csv")

    archivo = max(archivos, key=lambda x: x.stat().st_mtime)
    print(f"Cargando: {archivo.name}")

    df = pd.read_csv(archivo, encoding="utf-8-sig")
    return df


def normalizar_institucion(inst):
    """Acorta nombres de instituciones."""
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
        "Universidad La República": "ULAR",
        "Universidad de La Frontera": "UFRO",
        "University of Bío-Bío": "UBB",
        "Millennium Science Initiative": "ICM",
        "Universidad de Los Lagos": "U. Los Lagos",
        "Universidad Católica del Norte": "UCN",
        "Universidad de Tarapacá": "UTA",
        "Universidad Católica de Temuco": "UC Temuco",
        "Universidad Católica del Maule": "UCM",
        "Universidad de Atacama": "UDA",
        "Universidad de Antofagasta": "UA",
        "Universidad de Magallanes": "UMAG",
        "Universidad Arturo Prat": "UNAP",
        "Universidad de Playa Ancha de Ciencias de la Educación": "UPLA",
        "Universidad Metropolitana de Ciencias de la Educación": "UMCE",
        "Universidad Tecnológica Metropolitana": "UTEM",
        "Universidad Central de Chile": "UCEN",
        "Universidad Academia de Humanismo Cristiano": "UAHC",
        "Universidad SEK": "USEK",
        "Universidad Autónoma de Chile": "UA Chile",
        "Universidad Santo Tomás": "UST",
        "Universidad Gabriela Mistral": "UGM",
        "Universidad Bernardo O'Higgins": "UBO",
    }
    return mapeo.get(inst, inst[:20] if len(inst) > 20 else inst)


def abreviar_disciplina(d):
    """Abrevia disciplina."""
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
    return mapeo.get(d, d[:4])


def limpiar_topics(topics_str):
    """Limpia y acorta los topics."""
    if pd.isna(topics_str) or not topics_str:
        return ""

    # Tomar primeros 3 topics
    topics = str(topics_str).split(";")[:3]

    # Limpiar cada topic
    limpios = []
    for t in topics:
        t = t.strip()
        # Quitar palabras comunes
        t = t.replace(" and ", ", ").replace(" in ", " ")
        # Acortar
        if len(t) > 35:
            t = t[:32] + "..."
        limpios.append(t)

    return "; ".join(limpios)


def generar_js_array(df):
    """Genera el array JavaScript de investigadores."""
    investigadores = []

    for _, row in df.iterrows():
        # Scholar ID
        scholar_id = row.get("scholar_id", "")
        if pd.isna(scholar_id):
            scholar_id = ""

        # ORCID
        orcid = row.get("orcid", "")
        if pd.isna(orcid):
            orcid = ""

        # OpenAlex ID
        openalex_id = row.get("openalex_id", "")
        if pd.isna(openalex_id):
            openalex_id = ""

        # Trabajos
        works = row.get("trabajos", 0)
        if pd.isna(works):
            works = 0

        # Nombre sin caracteres especiales para JS
        nombre = str(row["nombre"]).replace('"', '\\"').replace("'", "\\'")
        nombre = nombre.replace("‐", "-").replace("–", "-")

        inv = {
            "id": str(scholar_id),
            "oaid": str(openalex_id),
            "name": nombre,
            "affiliation": normalizar_institucion(str(row["institucion"])),
            "d1": abreviar_disciplina(str(row["disciplina"])),
            "orcid": str(orcid),
            "topics": limpiar_topics(row.get("topics", "")),
            "hindex": int(row["h_index"]),
            "citations": int(row["citas"]),
            "works": int(works),
        }
        investigadores.append(inv)

    return investigadores


def generar_ranking_institucional(investigadores):
    """Genera ranking agregado por institución."""
    from collections import defaultdict

    inst_data = defaultdict(lambda: {"researchers": 0, "h_sum": 0, "citations": 0, "works": 0, "h_values": []})

    for r in investigadores:
        inst = r["affiliation"]
        inst_data[inst]["researchers"] += 1
        inst_data[inst]["h_sum"] += r["hindex"]
        inst_data[inst]["h_values"].append(r["hindex"])
        inst_data[inst]["citations"] += r["citations"]
        inst_data[inst]["works"] += r["works"]

    ranking = []
    for inst, data in inst_data.items():
        ranking.append({
            "name": inst,
            "researchers": data["researchers"],
            "h_avg": round(data["h_sum"] / data["researchers"], 1),
            "h_max": max(data["h_values"]),
            "citations": data["citations"],
            "works": data["works"]
        })

    # Ordenar por número de investigadores
    ranking.sort(key=lambda x: x["researchers"], reverse=True)
    return ranking


def generar_html(investigadores):
    """Genera el HTML completo."""

    # Estadísticas
    total = len(investigadores)
    avg_h = sum(r["hindex"] for r in investigadores) / total if total > 0 else 0
    total_citas = sum(r["citations"] for r in investigadores)
    instituciones = len(set(r["affiliation"] for r in investigadores))

    # Ranking institucional
    ranking_inst = generar_ranking_institucional(investigadores)

    # Lista de instituciones para el filtro
    lista_instituciones = sorted(set(r["affiliation"] for r in investigadores))

    # Convertir a JSON para JavaScript
    js_data = json.dumps(investigadores, ensure_ascii=False, indent=12)
    js_inst_data = json.dumps(ranking_inst, ensure_ascii=False, indent=12)
    js_inst_list = json.dumps(lista_instituciones, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ranking Chileno de Ciencias Sociales</title>
    <meta name="description" content="Ranking de impacto academico de cientificos sociales chilenos basado en OpenAlex">
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&family=Source+Serif+Pro:wght@600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #fff;
            color: #222;
            line-height: 1.5;
            font-size: 13px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 0 16px; }}
        header {{ border-bottom: 1px solid #e5e5e5; padding: 12px 0 10px; }}
        header h1 {{
            font-family: 'Source Serif Pro', Georgia, serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: #111;
            margin-bottom: 2px;
        }}
        header .subtitle {{ color: #666; font-size: 0.75rem; }}

        .description {{
            padding: 12px 0;
            border-bottom: 1px solid #e5e5e5;
        }}
        .description p {{
            font-size: 0.75rem;
            color: #444;
            margin-bottom: 6px;
            line-height: 1.5;
        }}
        .description a {{ color: #1565c0; }}
        .description .meta {{ font-size: 0.65rem; color: #888; margin-top: 8px; margin-bottom: 0; }}

        .stats {{
            display: flex;
            gap: 24px;
            padding: 10px 0;
            border-bottom: 1px solid #e5e5e5;
        }}
        .stat {{ text-align: left; }}
        .stat-value {{
            font-family: 'Source Serif Pro', Georgia, serif;
            font-size: 1rem;
            font-weight: 700;
            color: #111;
        }}
        .stat-label {{
            font-size: 0.55rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .filters {{
            padding: 12px 0;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .filters select, .filters input {{
            padding: 4px 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 0.75rem;
            font-family: inherit;
            background: #fff;
            color: #333;
        }}
        .filters select:focus, .filters input:focus {{ outline: none; border-color: #111; }}
        .filters input {{ width: 180px; }}
        .filters label {{ font-size: 0.7rem; color: #666; }}

        .tabs {{
            display: flex;
            gap: 0;
            border-bottom: 1px solid #e5e5e5;
            margin-bottom: 0;
        }}
        .tab {{
            padding: 8px 14px;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 500;
            color: #666;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .tab:hover {{ color: #111; }}
        .tab.active {{
            color: #111;
            border-bottom-color: #111;
        }}

        .table-wrapper {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead th {{
            text-align: left;
            padding: 6px 8px 6px 0;
            font-size: 0.6rem;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            border-bottom: 1px solid #111;
            cursor: pointer;
            white-space: nowrap;
        }}
        thead th:hover {{ color: #111; }}
        thead th.num {{ text-align: right; padding-right: 0; padding-left: 8px; }}
        tbody tr {{ border-bottom: 1px solid #eee; }}
        tbody tr:hover {{ background: #fafafa; }}
        tbody td {{ padding: 4px 6px 4px 0; vertical-align: middle; }}
        tbody td.num {{
            text-align: right;
            padding-right: 0;
            padding-left: 8px;
            font-variant-numeric: tabular-nums;
        }}

        .rank-num {{ font-weight: 600; color: #888; font-size: 0.75rem; }}
        .researcher-name {{ font-weight: 600; color: #111; font-size: 0.8rem; display: inline; }}
        .researcher-name a {{ color: #111; text-decoration: none; }}
        .researcher-name a:hover {{ text-decoration: underline; }}
        .researcher-affiliation {{ font-size: 0.7rem; color: #666; display: inline; }}
        .profile-links {{ display: inline; margin-left: 4px; }}
        .profile-link {{
            font-size: 0.55rem;
            padding: 1px 3px;
            border-radius: 2px;
            text-decoration: none;
            margin-left: 2px;
        }}
        .profile-link.orcid {{ background: #a6ce39; color: white; }}
        .profile-link.scholar {{ background: #4285f4; color: white; }}
        .profile-link:hover {{ opacity: 0.8; }}
        .discipline-tag {{
            display: inline-block;
            font-size: 0.6rem;
            padding: 1px 4px;
            border-radius: 2px;
            background: #f5f5f5;
            color: #555;
        }}
        .discipline-tag.cpol {{ background: #e3f2fd; color: #1565c0; }}
        .discipline-tag.soc {{ background: #fce4ec; color: #c62828; }}
        .discipline-tag.econ {{ background: #e8f5e9; color: #2e7d32; }}
        .discipline-tag.adm {{ background: #fff3e0; color: #e65100; }}
        .discipline-tag.psic {{ background: #f3e5f5; color: #7b1fa2; }}
        .discipline-tag.educ {{ background: #e0f7fa; color: #00838f; }}
        .discipline-tag.hum {{ background: #fbe9e7; color: #bf360c; }}
        .discipline-tag.com {{ background: #e8eaf6; color: #3f51b5; }}
        .h-value {{ font-weight: 700; color: #111; font-size: 0.8rem; }}
        .citation-value {{ color: #555; font-size: 0.8rem; }}
        .works-link {{ color: #1565c0; text-decoration: none; font-size: 0.8rem; }}
        .works-link:hover {{ text-decoration: underline; }}
        .topics {{ font-size: 0.65rem; color: #777; max-width: 220px; }}

        footer {{
            border-top: 1px solid #e5e5e5;
            margin-top: 24px;
            padding: 16px 0;
        }}
        .methodology {{ margin-bottom: 16px; }}
        .methodology h2 {{
            font-family: 'Source Serif Pro', Georgia, serif;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: #111;
        }}
        .methodology p {{ font-size: 0.7rem; color: #555; margin-bottom: 4px; }}
        .methodology a {{ color: #111; }}
        .footer-meta {{ font-size: 0.65rem; color: #999; }}
        .footer-meta a {{ color: #666; }}

        .download-btn {{
            padding: 4px 10px;
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 0.7rem;
            cursor: pointer;
            color: #333;
            text-decoration: none;
            margin-left: auto;
        }}
        .download-btn:hover {{ background: #eee; border-color: #ccc; }}

        .inst-table {{ margin-top: 12px; }}
        .inst-table th, .inst-table td {{ padding: 6px 10px 6px 0; }}
        .inst-name {{ font-weight: 600; color: #111; }}
        .section {{ display: none; }}
        .section.active {{ display: block; }}

        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.1rem; }}
            .stats {{ flex-wrap: wrap; gap: 16px; }}
            .filters {{ flex-direction: column; align-items: flex-start; }}
            .filters input {{ width: 100%; }}
            thead th, tbody td {{ padding: 4px 4px 4px 0; font-size: 0.6rem; }}
            .researcher-affiliation {{ font-size: 0.55rem; }}
            .tabs {{ overflow-x: auto; }}
            .tab {{ padding: 6px 10px; font-size: 0.65rem; white-space: nowrap; }}
            .topics {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Ranking Chileno de Ciencias Sociales</h1>
            <p class="subtitle">Impacto academico de investigadores en ciencias sociales en Chile</p>
        </header>

        <div class="description">
            <p>Este ranking mide el impacto academico de investigadores en ciencias sociales afiliados a instituciones chilenas, utilizando datos de <a href="https://openalex.org/" target="_blank">OpenAlex</a>.</p>
            <p>El proyecto se inspira en el <a href="https://github.com/bgonzalezbustamante/CPS-Ranking" target="_blank">CPS-Ranking</a> de Bastian Gonzalez-Bustamante, expandiendo la cobertura desde ciencia politica hacia todas las ciencias sociales: sociologia, economia, psicologia, educacion, comunicacion y mas.</p>
            <p class="meta">Actualizacion: {datetime.now().strftime("%B %Y")} | Fuente: OpenAlex API | H-index minimo: 2</p>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="stat-total">{total}</div>
                <div class="stat-label">Investigadores</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-h">{avg_h:.1f}</div>
                <div class="stat-label">H-index promedio</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-citas">{total_citas:,}</div>
                <div class="stat-label">Citas totales</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-inst">{instituciones}</div>
                <div class="stat-label">Instituciones</div>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="setSection('researchers')">Investigadores</div>
            <div class="tab" onclick="setSection('institutions')">Por Institucion</div>
        </div>

        <div id="section-researchers" class="section active">
            <div class="filters">
                <label for="filter-discipline">Disciplina:</label>
                <select id="filter-discipline" onchange="filterTable()">
                    <option value="">Todas</option>
                    <option value="C.Pol">Ciencia Politica</option>
                    <option value="Soc">Sociologia</option>
                    <option value="Econ">Economia</option>
                    <option value="Adm">Administracion</option>
                    <option value="Psic">Psicologia</option>
                    <option value="Educ">Educacion</option>
                    <option value="Hum">Humanidades</option>
                    <option value="Com">Comunicacion</option>
                </select>
                <label for="filter-inst">Institucion:</label>
                <select id="filter-inst" onchange="filterTable()">
                    <option value="">Todas</option>
                </select>
                <input type="text" id="search" placeholder="Buscar nombre..." oninput="filterTable()">
                <label style="margin-left: 8px;">Ordenar:</label>
                <select id="sort-by" onchange="filterTable()">
                    <option value="hindex">H-index</option>
                    <option value="citations">Citas</option>
                    <option value="works">Trabajos</option>
                </select>
                <button class="download-btn" onclick="downloadCSV()">Descargar CSV</button>
            </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th style="width: 35px;">#</th>
                        <th>Investigador/a</th>
                        <th>Disciplina</th>
                        <th>Temas de investigacion</th>
                        <th class="num">H-index</th>
                        <th class="num">Citas</th>
                        <th class="num">Trabajos</th>
                    </tr>
                </thead>
                <tbody id="ranking-body">
                </tbody>
            </table>
        </div>
        </div>

        <div id="section-institutions" class="section">
            <div class="filters">
                <label style="margin-left: 0;">Ordenar por:</label>
                <select id="sort-inst" onchange="renderInstTable()">
                    <option value="researchers">N de investigadores</option>
                    <option value="h_avg">H-index promedio</option>
                    <option value="h_max">H-index maximo</option>
                    <option value="citations">Citas totales</option>
                </select>
            </div>
            <div class="table-wrapper">
                <table class="inst-table">
                    <thead>
                        <tr>
                            <th style="width: 35px;">#</th>
                            <th>Institucion</th>
                            <th class="num">Investigadores</th>
                            <th class="num">H-index prom.</th>
                            <th class="num">H-index max.</th>
                            <th class="num">Citas</th>
                            <th class="num">Trabajos</th>
                        </tr>
                    </thead>
                    <tbody id="inst-body">
                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            <div class="methodology">
                <h2>Metodologia</h2>
                <p><strong>Fuente:</strong> <a href="https://openalex.org/" target="_blank">OpenAlex</a> - Base de datos abierta con 240M+ trabajos academicos indexados.</p>
                <p><strong>Criterios:</strong> Afiliacion actual en institucion chilena, dominio "Social Sciences", h-index >= 2.</p>
                <p><strong>Disciplinas:</strong> Clasificacion automatica segun topics de OpenAlex.</p>
                <p><strong>Limitaciones:</strong> OpenAlex puede no incluir todas las publicaciones. Clasificacion disciplinar aproximada.</p>
            </div>
            <div class="footer-meta">
                <p>Datos: <a href="https://openalex.org/" target="_blank">OpenAlex</a> | Licencia: <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY-4.0</a></p>
            </div>
        </footer>
    </div>

    <script>
        const researchers = {js_data};
        const institutions = {js_inst_data};
        const instList = {js_inst_list};

        let currentData = [...researchers];

        // Poblar dropdown de instituciones
        const instSelect = document.getElementById('filter-inst');
        instList.forEach(inst => {{
            const opt = document.createElement('option');
            opt.value = inst;
            opt.textContent = inst;
            instSelect.appendChild(opt);
        }});

        function formatNumber(n) {{
            return n.toLocaleString('es-CL');
        }}

        function getDisciplineClass(d) {{
            const classes = {{
                'C.Pol': 'cpol', 'Soc': 'soc', 'Econ': 'econ', 'Adm': 'adm',
                'Psic': 'psic', 'Educ': 'educ', 'Hum': 'hum', 'Com': 'com', 'CS': ''
            }};
            return classes[d] || '';
        }}

        function getDisciplineName(d) {{
            const names = {{
                'C.Pol': 'C. Politica', 'Soc': 'Sociologia', 'Econ': 'Economia',
                'Adm': 'Administracion', 'Psic': 'Psicologia', 'Educ': 'Educacion',
                'Hum': 'Humanidades', 'Com': 'Comunicacion', 'CS': 'Cs. Sociales'
            }};
            return names[d] || d;
        }}

        function setSection(section) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById('section-' + section).classList.add('active');
            if (section === 'institutions') {{
                renderInstTable();
            }}
        }}

        function renderTable(data) {{
            const tbody = document.getElementById('ranking-body');
            tbody.innerHTML = data.map((r, i) => {{
                const nameHtml = `<a href="https://openalex.org/authors/${{r.oaid}}" target="_blank" title="Ver perfil en OpenAlex">${{r.name}}</a>`;
                let linksHtml = '<span class="profile-links">';
                if (r.orcid) {{
                    linksHtml += `<a href="https://orcid.org/${{r.orcid}}" target="_blank" class="profile-link orcid" title="ORCID">iD</a>`;
                }}
                if (r.id) {{
                    linksHtml += `<a href="https://scholar.google.com/citations?user=${{r.id}}" target="_blank" class="profile-link scholar" title="Google Scholar">GS</a>`;
                }}
                linksHtml += '</span>';
                return `
                <tr>
                    <td><span class="rank-num">${{i + 1}}</span></td>
                    <td><span class="researcher-name">${{nameHtml}}</span>${{linksHtml}}, <span class="researcher-affiliation">${{r.affiliation}}</span></td>
                    <td><span class="discipline-tag ${{getDisciplineClass(r.d1)}}">${{getDisciplineName(r.d1)}}</span></td>
                    <td><span class="topics">${{r.topics}}</span></td>
                    <td class="num"><span class="h-value">${{r.hindex}}</span></td>
                    <td class="num"><span class="citation-value">${{formatNumber(r.citations)}}</span></td>
                    <td class="num"><a href="https://openalex.org/authors/${{r.oaid}}/works" target="_blank" class="works-link" title="Ver trabajos en OpenAlex">${{r.works}}</a></td>
                </tr>
            `}}).join('');
        }}

        function renderInstTable() {{
            const sortBy = document.getElementById('sort-inst').value;
            const sorted = [...institutions].sort((a, b) => b[sortBy] - a[sortBy]);

            const tbody = document.getElementById('inst-body');
            tbody.innerHTML = sorted.map((inst, i) => `
                <tr>
                    <td><span class="rank-num">${{i + 1}}</span></td>
                    <td><span class="inst-name">${{inst.name}}</span></td>
                    <td class="num">${{inst.researchers}}</td>
                    <td class="num">${{inst.h_avg}}</td>
                    <td class="num">${{inst.h_max}}</td>
                    <td class="num">${{formatNumber(inst.citations)}}</td>
                    <td class="num">${{formatNumber(inst.works)}}</td>
                </tr>
            `).join('');
        }}

        function filterTable() {{
            const discipline = document.getElementById('filter-discipline').value;
            const inst = document.getElementById('filter-inst').value;
            const search = document.getElementById('search').value.toLowerCase();
            const sortBy = document.getElementById('sort-by').value;

            currentData = researchers.filter(r => {{
                const matchD = !discipline || r.d1 === discipline;
                const matchI = !inst || r.affiliation === inst;
                const matchS = !search ||
                    r.name.toLowerCase().includes(search) ||
                    r.topics.toLowerCase().includes(search);
                return matchD && matchI && matchS;
            }});

            currentData.sort((a, b) => b[sortBy] - a[sortBy]);

            renderTable(currentData);
            updateStats();
        }}

        function updateStats() {{
            const total = currentData.length;
            const avgH = total > 0 ? (currentData.reduce((s, r) => s + r.hindex, 0) / total).toFixed(1) : 0;
            const totalCitas = currentData.reduce((s, r) => s + r.citations, 0);
            const insts = new Set(currentData.map(r => r.affiliation)).size;

            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-h').textContent = avgH;
            document.getElementById('stat-citas').textContent = formatNumber(totalCitas);
            document.getElementById('stat-inst').textContent = insts;
        }}

        function downloadCSV() {{
            const headers = ['Ranking', 'Nombre', 'Institucion', 'Disciplina', 'H-index', 'Citas', 'Trabajos', 'ORCID', 'OpenAlex ID'];
            const rows = currentData.map((r, i) => [
                i + 1,
                r.name,
                r.affiliation,
                getDisciplineName(r.d1),
                r.hindex,
                r.citations,
                r.works,
                r.orcid || '',
                r.oaid || ''
            ]);

            let csv = headers.join(',') + '\\n';
            rows.forEach(row => {{
                csv += row.map(cell => `"${{String(cell).replace(/"/g, '""')}}"`).join(',') + '\\n';
            }});

            const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'ranking_ciencias_sociales_chile.csv';
            link.click();
        }}

        filterTable();
    </script>
</body>
</html>'''

    return html


def main():
    print("Generando HTML del ranking...")

    # Cargar datos
    df = cargar_datos()
    print(f"Cargados {len(df)} investigadores")

    # Generar array JS
    investigadores = generar_js_array(df)

    # Generar HTML
    html = generar_html(investigadores)

    # Guardar
    output_path = DOCS_DIR / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML guardado: {output_path}")
    print(f"Total investigadores: {len(investigadores)}")


if __name__ == "__main__":
    main()
