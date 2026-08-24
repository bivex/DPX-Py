"""HTML Report Formatter implementing ReportFormatterPort with Semantic UI (Fomantic-UI)."""

from __future__ import annotations

import html

from pattern_detector.domain.detection import DetectionReport
from pattern_detector.domain.value_objects import ConfidenceLevel, PatternCategory, PatternType
from pattern_detector.ports.outbound import ReportFormatterPort

CATEGORY_STYLES: dict[PatternCategory, dict[str, str]] = {
    PatternCategory.CREATIONAL: {
        "text": "#34d399",
        "bg": "#064e3b44",
        "border": "#059669",
        "accent": "#10b981",
        "label_color": "green",
        "icon": "magic",
        "name": "Creational",
    },
    PatternCategory.STRUCTURAL: {
        "text": "#38bdf8",
        "bg": "#0c4a6e44",
        "border": "#0284c7",
        "accent": "#0ea5e9",
        "label_color": "blue",
        "icon": "cubes",
        "name": "Structural",
    },
    PatternCategory.BEHAVIORAL: {
        "text": "#c084fc",
        "bg": "#581c8744",
        "border": "#9333ea",
        "accent": "#a855f7",
        "label_color": "purple",
        "icon": "sync alternate",
        "name": "Behavioral",
    },
    PatternCategory.ARCHITECTURAL: {
        "text": "#fbbf24",
        "bg": "#78350f44",
        "border": "#d97706",
        "accent": "#f59e0b",
        "label_color": "orange",
        "icon": "building",
        "name": "Architectural",
    },
    PatternCategory.CONCURRENCY: {
        "text": "#fb7185",
        "bg": "#88133744",
        "border": "#e11d48",
        "accent": "#f43f5e",
        "label_color": "red",
        "icon": "microchip",
        "name": "Concurrency",
    },
    PatternCategory.PRINCIPLE: {
        "text": "#818cf8",
        "bg": "#312e8144",
        "border": "#4f46e5",
        "accent": "#6366f1",
        "label_color": "teal",
        "icon": "shield alternate",
        "name": "Principles & SOLID",
    },
}

PATTERN_TYPE_COLORS: dict[PatternType, dict[str, str]] = {
    PatternType.OBSERVER: {"text": "#f472b6", "bg": "#83184344", "border": "#db2777", "label": "pink"},
    PatternType.STRATEGY: {"text": "#a78bfa", "bg": "#4c1d9544", "border": "#7c3aed", "label": "violet"},
    PatternType.DECORATOR: {"text": "#38bdf8", "bg": "#0c4a6e44", "border": "#0284c7", "label": "blue"},
    PatternType.CHAIN_OF_RESPONSIBILITY: {"text": "#818cf8", "bg": "#312e8144", "border": "#4f46e5", "label": "purple"},
    PatternType.TEMPLATE_METHOD: {"text": "#60a5fa", "bg": "#1e3a8a44", "border": "#2563eb", "label": "blue"},
    PatternType.COMMAND: {"text": "#fb923c", "bg": "#7c2d1244", "border": "#ea580c", "label": "orange"},
    PatternType.STATE: {"text": "#e879f9", "bg": "#701a7544", "border": "#c026d3", "label": "pink"},
    PatternType.SINGLETON: {"text": "#4ade80", "bg": "#14532d44", "border": "#16a34a", "label": "green"},
    PatternType.FACTORY_METHOD: {"text": "#2dd4bf", "bg": "#134e4a44", "border": "#0d9488", "label": "teal"},
    PatternType.ABSTRACT_FACTORY: {"text": "#a3e635", "bg": "#36531444", "border": "#65a30d", "label": "olive"},
    PatternType.BUILDER: {"text": "#86efac", "bg": "#14532d44", "border": "#22c55e", "label": "green"},
    PatternType.ADAPTER: {"text": "#67e8f9", "bg": "#164e6344", "border": "#0891b2", "label": "teal"},
    PatternType.FACADE: {"text": "#22d3ee", "bg": "#155e7544", "border": "#06b6d4", "label": "teal"},
    PatternType.PROXY: {"text": "#93c5fd", "bg": "#1e3a8a44", "border": "#3b82f6", "label": "blue"},
    PatternType.FLYWEIGHT: {"text": "#5eead4", "bg": "#134e4a44", "border": "#14b8a6", "label": "teal"},
    PatternType.LIFECYCLE_COMPONENT: {"text": "#fcd34d", "bg": "#78350f44", "border": "#d97706", "label": "yellow"},
    PatternType.CIRCULAR_DEPENDENCY: {"text": "#f87171", "bg": "#7f1d1d44", "border": "#dc2626", "label": "red"},
    PatternType.PROTOTYPE: {"text": "#86efac", "bg": "#14532d44", "border": "#22c55e", "label": "green"},
    PatternType.COMPOSITE: {"text": "#38bdf8", "bg": "#0c4a6e44", "border": "#0284c7", "label": "blue"},
    PatternType.BRIDGE: {"text": "#67e8f9", "bg": "#164e6344", "border": "#0891b2", "label": "teal"},
    PatternType.ITERATOR: {"text": "#a78bfa", "bg": "#4c1d9544", "border": "#7c3aed", "label": "violet"},
    PatternType.MEDIATOR: {"text": "#fb923c", "bg": "#7c2d1244", "border": "#ea580c", "label": "orange"},
    PatternType.MEMENTO: {"text": "#e879f9", "bg": "#701a7544", "border": "#c026d3", "label": "pink"},
    PatternType.VISITOR: {"text": "#f472b6", "bg": "#83184344", "border": "#db2777", "label": "pink"},
    PatternType.INTERPRETER: {"text": "#60a5fa", "bg": "#1e3a8a44", "border": "#2563eb", "label": "blue"},
    PatternType.SINGLE_RESPONSIBILITY: {"text": "#818cf8", "bg": "#312e8144", "border": "#4f46e5", "label": "teal"},
    PatternType.OPEN_CLOSED: {"text": "#a78bfa", "bg": "#4c1d9544", "border": "#7c3aed", "label": "violet"},
    PatternType.LISKOV_SUBSTITUTION: {"text": "#f472b6", "bg": "#83184344", "border": "#db2777", "label": "red"},
    PatternType.INTERFACE_SEGREGATION: {"text": "#38bdf8", "bg": "#0c4a6e44", "border": "#0284c7", "label": "blue"},
    PatternType.DEPENDENCY_INVERSION: {"text": "#34d399", "bg": "#064e3b44", "border": "#059669", "label": "green"},
    PatternType.COMPOSITION_OVER_INHERITANCE: {"text": "#2dd4bf", "bg": "#134e4a44", "border": "#0d9488", "label": "teal"},
    PatternType.LAW_OF_DEMETER: {"text": "#fbbf24", "bg": "#78350f44", "border": "#d97706", "label": "yellow"},
    PatternType.HIGH_COHESION_LOW_COUPLING: {"text": "#60a5fa", "bg": "#1e3a8a44", "border": "#2563eb", "label": "blue"},
    PatternType.KISS: {"text": "#a3e635", "bg": "#36531444", "border": "#65a30d", "label": "olive"},
    PatternType.DRY: {"text": "#e879f9", "bg": "#701a7544", "border": "#c026d3", "label": "pink"},
}


class HtmlReportFormatter(ReportFormatterPort):
    """Renders a standalone, responsive, interactive Semantic UI (Fomantic-UI) HTML dashboard for DetectionReport."""

    def format(self, report: DetectionReport, verbose: bool = False) -> str:
        vh_count = sum(1 for d in report.detections if d.level == ConfidenceLevel.VERY_HIGH)
        h_count = sum(1 for d in report.detections if d.level == ConfidenceLevel.HIGH)
        m_count = sum(1 for d in report.detections if d.level == ConfidenceLevel.MEDIUM)
        l_count = sum(1 for d in report.detections if d.level == ConfidenceLevel.LOW)

        cards_html: list[str] = []
        for idx, det in enumerate(report.detections, 1):
            cat_style = CATEGORY_STYLES.get(
                det.pattern_category,
                {"text": "#94a3b8", "bg": "#1e293b44", "border": "#475569", "accent": "#64748b", "label_color": "grey", "icon": "tag", "name": "Other"},
            )
            pat_style = PATTERN_TYPE_COLORS.get(
                det.pattern_type,
                {"text": "#38bdf8", "bg": "#0c4a6e44", "border": "#0284c7", "label": "blue"},
            )

            badge_color = {
                ConfidenceLevel.VERY_HIGH: "green",
                ConfidenceLevel.HIGH: "teal",
                ConfidenceLevel.MEDIUM: "orange",
                ConfidenceLevel.LOW: "red",
            }.get(det.level, "blue")

            evidences_html: list[str] = []
            for ev in det.evidences:
                pct = int(ev.weight * 100)
                loc_str = f'<span class="location-tag"><i class="map marker alternate icon"></i> {html.escape(str(ev.location))}</span>' if ev.location else ""
                evidences_html.append(
                    f'<div class="item" style="padding: 4px 0; border-left: 3px solid {cat_style["accent"]}; padding-left: 10px; margin-bottom: 4px;">'
                    f'<span class="weight-tag" style="color: {cat_style["text"]}; font-weight: 700; font-family: monospace;">+{pct}%</span> '
                    f'<span class="rule-code" style="color: #94a3b8; font-family: monospace; font-size: 11px;">[{html.escape(ev.rule_code)}]</span> '
                    f'<span style="color: #e2e8f0;">{html.escape(ev.description)}</span> {loc_str}'
                    f"</div>"
                )

            related_html = ""
            if det.related_locations:
                rel_items = " ".join(f'<span class="code-pill"><i class="file code outline icon"></i> {html.escape(str(loc))}</span>' for loc in det.related_locations)
                related_html = f'<div style="margin-top: 10px; font-size: 12px; color: #94a3b8;"><strong>Related Locations:</strong><div style="margin-top: 4px;">{rel_items}</div></div>'

            cards_html.append(
                f"""
                <div class="ui fluid inverted card pattern-card" data-pattern="{html.escape(det.pattern_type.value)}" data-category="{html.escape(det.pattern_category.value)}" data-target="{html.escape(det.target_name)}" style="background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid {cat_style["accent"]} !important; margin-bottom: 14px;">
                    <div class="content" style="border-bottom: 1px solid #1e293b; padding: 12px 16px;">
                        <div class="right floated">
                            <span class="ui mini {badge_color} label" style="font-weight: 700;">{det.confidence.percentage_str} [{det.level.value}]</span>
                        </div>
                        <div class="header" style="color: #f8fafc; font-size: 15px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <span style="color: #64748b; font-weight: 700; font-size: 13px;">#{idx}</span>
                            <span class="ui mini {cat_style['label_color']} label"><i class="{cat_style['icon']} icon"></i> {html.escape(cat_style["name"].upper())}</span>
                            <span class="ui mini {pat_style['label']} label">{html.escape(det.pattern_type.value.upper())}</span>
                            <span style="color: #cbd5e1; font-weight: 600;">{html.escape(det.target_kind)}:</span>
                            <span style="color: #38bdf8; font-family: monospace; font-weight: 700;">{html.escape(det.target_name)}</span>
                        </div>
                    </div>
                    <div class="content" style="padding: 14px 16px; font-size: 13px;">
                        <div style="margin-bottom: 8px; color: #e2e8f0; font-size: 14px;">
                            <i class="info circle icon" style="color: #38bdf8;"></i> <strong>Summary:</strong> {html.escape(det.summary)}
                        </div>
                        <div style="margin-bottom: 10px; color: #94a3b8;">
                            <i class="map marker alternate icon" style="color: #f43f5e;"></i> <strong>Primary Location:</strong> <span class="code-pill">{html.escape(str(det.primary_location))}</span>
                        </div>
                        <div class="evidence-section" style="margin-top: 12px;">
                            <div style="font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                                <i class="search icon"></i> Evidence Trail ({len(det.evidences)} heuristics):
                            </div>
                            <div class="ui inverted list">
                                {"".join(evidences_html)}
                            </div>
                        </div>
                        {related_html}
                    </div>
                </div>
                """
            )

        category_filters = []
        for cat_enum, style in CATEGORY_STYLES.items():
            count = report.summary_by_category.get(cat_enum.value, 0)
            if count > 0:
                category_filters.append(
                    f"""
                    <a class="item cat-filter-btn" data-filter="{cat_enum.value}">
                        <i class="{style['icon']} icon" style="color: {style['accent']};"></i>
                        {style['name']}
                        <div class="ui mini {style['label_color']} label">{count}</div>
                    </a>
                    """
                )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Scanner Report - {html.escape(report.project_path or "Codebase")}</title>
    <!-- Fomantic-UI (Semantic UI) CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.3/dist/semantic.min.css">
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.3/dist/semantic.min.js"></script>

    <style>
        :root {{
            --bg-page: #090d16;
            --bg-sidebar: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --accent-cyan: #38bdf8;
            --accent-purple: #c084fc;
            --accent-emerald: #34d399;
            --accent-rose: #f43f5e;
            --accent-amber: #fbbf24;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-page) !important;
            color: #f8fafc !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding-bottom: 40px;
        }}

        .ui.inverted.menu {{
            background: linear-gradient(135deg, #0b1329 0%, #1e1b4b 100%) !important;
            border-bottom: 1px solid #1e293b !important;
            margin-bottom: 24px !important;
            border-radius: 0 !important;
        }}

        .code-pill {{
            background: #1e293b;
            border: 1px solid #334155;
            padding: 2px 7px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: var(--accent-cyan);
            display: inline-block;
            margin: 2px 0;
        }}
        .location-tag {{
            color: #7dd3fc;
            font-size: 11px;
            margin-left: 8px;
        }}

        .pattern-card {{
            transition: all 0.2s ease;
        }}
        .pattern-card:hover {{
            border-color: var(--accent-cyan) !important;
            box-shadow: 0 4px 20px rgba(56, 189, 248, 0.15) !important;
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>

    <!-- Semantic UI Top Menu -->
    <div class="ui inverted borderless menu">
        <div class="ui container">
            <div class="header item">
                <i class="shield alternate icon" style="color: #38bdf8;"></i>
                <span style="font-weight: 700; font-size: 16px; margin-left: 6px;">DPX-Py Pattern Scanner Report</span>
            </div>
            <div class="item">
                <span class="ui mini blue label"><i class="folder open outline icon"></i> {html.escape(report.project_path or "Project Repository")}</span>
            </div>
            <div class="right menu">
                <div class="item">
                    <span class="ui mini teal label"><i class="bolt icon"></i> Hexagonal DDD Parser</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Container -->
    <div class="ui container">

        <!-- KPI Statistics -->
        <div class="ui inverted segment" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 20px; padding: 16px 20px;">
            <div class="ui five mini inverted statistics">
                <div class="statistic">
                    <div class="value" style="color: #38bdf8;">{report.total_detections_count}</div>
                    <div class="label" style="color: #94a3b8;">Total Detections</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #4ade80;">{vh_count + h_count}</div>
                    <div class="label" style="color: #94a3b8;">High Confidence (≥70%)</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #fbbf24;">{m_count + l_count}</div>
                    <div class="label" style="color: #94a3b8;">Med / Low (<70%)</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #c084fc;">{report.scanned_files_count}</div>
                    <div class="label" style="color: #94a3b8;">Files Scanned</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #34d399;">{report.elapsed_seconds:.3f}s</div>
                    <div class="label" style="color: #94a3b8;">Scan Duration</div>
                </div>
            </div>
        </div>

        <!-- Filter Menu (Semantic UI Secondary Pointing Menu) -->
        <div class="ui mini inverted secondary pointing menu" style="border-bottom: 1px solid #1e293b; margin-bottom: 16px;">
            <a class="active item cat-filter-btn" data-filter="all">
                <i class="cubes icon"></i> All Categories
                <div class="ui mini blue label">{report.total_detections_count}</div>
            </a>
            {"".join(category_filters)}
        </div>

        <!-- Search Bar -->
        <div class="ui fluid icon inverted input" style="margin-bottom: 20px;">
            <input type="text" id="searchInput" placeholder="🔎 Instant search by pattern name, category, target class/function, or rule (e.g. observer, singleton, strategy, dependency_inversion)..." style="background: #0f172a; border: 1px solid #1e293b; color: #f8fafc; padding: 12px 16px;">
            <i class="search icon"></i>
        </div>

        <!-- Pattern Cards Container -->
        <div id="cardsContainer">
            {"".join(cards_html)}
        </div>
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const cards = document.querySelectorAll('.pattern-card');
        const filterBtns = document.querySelectorAll('.cat-filter-btn');
        let selectedCategory = 'all';

        function filterCards() {{
            const query = searchInput.value.toLowerCase();
            let visibleCount = 0;

            cards.forEach(card => {{
                const text = card.textContent.toLowerCase();
                const pattern = card.dataset.pattern || '';
                const category = card.dataset.category || '';
                const target = card.dataset.target || '';

                const matchesCategory = (selectedCategory === 'all' || category === selectedCategory);
                const matchesSearch = (!query || text.includes(query) || pattern.includes(query) || category.includes(query) || target.includes(query));

                if (matchesCategory && matchesSearch) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        searchInput.addEventListener('input', filterCards);

        filterBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedCategory = btn.dataset.filter;
                filterCards();
            }});
        }});
    </script>
</body>
</html>
"""
