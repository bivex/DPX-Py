"""HTML Report Formatter implementing ReportFormatterPort with Semantic UI (Fomantic-UI)."""

from __future__ import annotations

import html
from typing import Any

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
    PatternType.COMPOSITION_OVER_INHERITANCE: {
        "text": "#2dd4bf",
        "bg": "#134e4a44",
        "border": "#0d9488",
        "label": "teal",
    },
    PatternType.LAW_OF_DEMETER: {"text": "#fbbf24", "bg": "#78350f44", "border": "#d97706", "label": "yellow"},
    PatternType.HIGH_COHESION_LOW_COUPLING: {
        "text": "#60a5fa",
        "bg": "#1e3a8a44",
        "border": "#2563eb",
        "label": "blue",
    },
    PatternType.KISS: {"text": "#a3e635", "bg": "#36531444", "border": "#65a30d", "label": "olive"},
    PatternType.DRY: {"text": "#e879f9", "bg": "#701a7544", "border": "#c026d3", "label": "pink"},
}


_VIOLATION_TERMS: tuple[str, ...] = (
    "violation",
    "smell",
    "god",
    "broken",
    "fat",
    "train_wreck",
    "duplicate",
    "complexity",
    "circular",
    "breach",
    "unsupported",
    "high_fan_out",
    "kiss_cyclomatic",
    "kiss_complexity",
)

_VIOLATION_SUMMARY_SUBSTRINGS: tuple[str, ...] = (
    "violation",
    "god class",
    "train wreck",
    "breaks parent contract",
    "circular dependency",
)

_VIOLATION_RULE_SUFFIXES: tuple[str, ...] = (
    "_VIOLATION",
    "_CASCADE",
    "_GOD_CLASS",
    "_MIXED_CONCERNS",
    "_FAT_INTERFACE",
    "_UNSUPPORTED_OPERATION",
    "_CONTRACT_BREACH",
    "_CONCRETE_INSTANTIATION",
    "_TRAIN_WRECK_CHAIN",
    "_HIGH_CYCLOMATIC_COMPLEXITY",
    "_LONG_PARAMETER_LIST",
    "_DEEP_INHERITANCE_TREE",
    "_DUPLICATE_BLOCK",
    "_HIGH_FAN_OUT",
    "_STRUCTURAL_COUPLING",
    "_FRAGILE_MODIFICATION",
)

_HTML_DASHBOARD_TEMPLATE: str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Scanner Report - {project_name}</title>
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

        .status-filter-btn.active {{
            background-color: #1e293b !important;
            font-weight: 700 !important;
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
                <span class="ui mini blue label"><i class="folder open outline icon"></i> {project_name}</span>
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
                    <div class="value" style="color: #38bdf8;">{total_detections}</div>
                    <div class="label" style="color: #94a3b8;">Total Detections</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #f87171;">{total_violations}</div>
                    <div class="label" style="color: #94a3b8;">⚠️ Needs Fix / Violations</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #4ade80;">{total_adherences}</div>
                    <div class="label" style="color: #94a3b8;">✅ Clean / Adherences</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #38bdf8;">{total_patterns}</div>
                    <div class="label" style="color: #94a3b8;">🔷 Design Patterns</div>
                </div>
                <div class="statistic">
                    <div class="value" style="color: #c084fc;">{scanned_files} files ({elapsed_seconds}s)</div>
                    <div class="label" style="color: #94a3b8;">Scan Scope</div>
                </div>
            </div>
        </div>

        <!-- Architectural Map & LLM Prompt Section -->
        <div class="ui inverted segment" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 20px; padding: 16px 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h3 style="color: #f8fafc; margin: 0; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                        <i class="magic icon" style="color: #c084fc;"></i>
                        <span>AI Architectural Map & LLM Context Prompt</span>
                    </h3>
                    <p style="color: #94a3b8; font-size: 13px; margin-top: 4px; margin-bottom: 0;">
                        Export structured codebase architecture map formatted for Claude, ChatGPT or Gemini to analyze bottlenecks and suggest improvements.
                    </p>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="ui mini inverted basic button" id="toggleArchMapBtn" onclick="toggleArchMapPreview()">
                        <i class="eye icon"></i> <span id="toggleArchMapText">View Map Preview</span>
                    </button>
                    <button class="ui mini purple button" id="copyLlmBtn" onclick="copyArchMapForLlm()" style="font-weight: 700;">
                        <i class="copy outline icon"></i> 📋 Copy Architecture Map for LLM
                    </button>
                </div>
            </div>

            <!-- Toast notification -->
            <div id="copyToast" class="ui positive mini message" style="display: none; padding: 10px 14px; margin-top: 12px; background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #86efac; border-radius: 6px;">
                <i class="check circle icon"></i> <strong>Copied to clipboard!</strong> Paste directly into your AI assistant (Claude, ChatGPT, Gemini) for instant architectural recommendations & refactoring suggestions.
            </div>

            <!-- Collapsible Preview Block -->
            <div id="archMapPreviewContainer" style="display: none; margin-top: 14px;">
                <div style="font-size: 12px; color: #64748b; margin-bottom: 6px; display: flex; justify-content: space-between;">
                    <span><i class="code icon"></i> Markdown Prompt & Architectural Context:</span>
                    <span>Optimized for AI prompt context</span>
                </div>
                <pre id="archMapPre" style="max-height: 380px; overflow-y: auto; background: #070b14; border: 1px solid #1e293b; color: #bae6fd; padding: 14px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word;">{llm_arch_map_preview}</pre>
            </div>

            <textarea id="llmArchMapRaw" style="display: none;">{llm_arch_map_raw}</textarea>
        </div>

        <!-- Filter Menu (Semantic UI Secondary Pointing Menu for Categories) -->
        <div class="ui mini inverted secondary pointing menu" style="border-bottom: 1px solid #1e293b; margin-bottom: 14px;">
            <a class="active item cat-filter-btn" data-filter="all">
                <i class="cubes icon"></i> All Categories
                <div class="ui mini blue label">{total_detections}</div>
            </a>
            {category_filters}
        </div>

        <!-- Action Status Sub-Tabs Bar -->
        <div class="ui inverted segment" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 16px; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="font-size: 13px; color: #94a3b8; font-weight: 600;">
                <i class="filter icon" style="color: #38bdf8;"></i> Findings Action Filter:
            </div>
            <div class="ui mini inverted basic buttons" id="statusFilterGroup">
                <button class="ui button active status-filter-btn" data-status="all">
                    <i class="eye icon"></i> All Findings <span class="ui mini blue label" id="statusCountAll">{total_detections}</span>
                </button>
                <button class="ui button status-filter-btn" data-status="violation" style="color: #f87171 !important;">
                    <i class="exclamation triangle icon" style="color: #f87171;"></i> ⚠️ Needs Fix (Violations) <span class="ui mini red label" id="statusCountViolation">{total_violations}</span>
                </button>
                <button class="ui button status-filter-btn" data-status="adherence" style="color: #4ade80 !important;">
                    <i class="check circle icon" style="color: #4ade80;"></i> ✅ Clean (Adherences) <span class="ui mini green label" id="statusCountAdherence">{total_adherences}</span>
                </button>
                <button class="ui button status-filter-btn" data-status="pattern" style="color: #38bdf8 !important;">
                    <i class="cube icon" style="color: #38bdf8;"></i> 🔷 Design Patterns <span class="ui mini teal label" id="statusCountPattern">{total_patterns}</span>
                </button>
            </div>
        </div>

        <!-- Search Bar -->
        <div class="ui fluid icon inverted input" style="margin-bottom: 20px;">
            <input type="text" id="searchInput" placeholder="🔎 Instant search by pattern name, category, target class/function, or rule (e.g. ocp, singleton, strategy, kiss)..." style="background: #0f172a; border: 1px solid #1e293b; color: #f8fafc; padding: 12px 16px;">
            <i class="search icon"></i>
        </div>

        <!-- Zero Violations Alert Message (shown when filtering by violation and 0 exist) -->
        <div id="noViolationsAlert" class="ui positive icon message" style="display: none; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); color: #86efac; margin-bottom: 20px; border-radius: 8px;">
            <i class="check circle outline icon" style="color: #34d399;"></i>
            <div class="content">
                <div class="header" style="color: #34d399; font-size: 16px; font-weight: 700;">Zero Violations Found!</div>
                <p style="color: #cbd5e1; margin-top: 4px;">All evaluated code conforms cleanly to SOLID & Clean Code architecture. No refactoring or bug fixes required.</p>
            </div>
        </div>

        <!-- No Matching Results Message -->
        <div id="noResultsMessage" class="ui inverted segment" style="display: none; background: #0f172a; border: 1px solid #1e293b; text-align: center; padding: 30px; border-radius: 8px;">
            <i class="search icon" style="font-size: 24px; color: #64748b; margin-bottom: 10px;"></i>
            <div style="color: #94a3b8; font-size: 15px;">No findings match the selected category, action status, or search query.</div>
        </div>

        <!-- Pattern Cards Container -->
        <div id="cardsContainer">
            {cards_html}
        </div>
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const cards = document.querySelectorAll('.pattern-card');
        const categoryBtns = document.querySelectorAll('.cat-filter-btn');
        const statusBtns = document.querySelectorAll('.status-filter-btn');
        const noViolationsAlert = document.getElementById('noViolationsAlert');
        const noResultsMessage = document.getElementById('noResultsMessage');

        let selectedCategory = 'all';
        let selectedStatus = 'all';

        function updateStatusCounts() {{
            let total = 0, violations = 0, adherences = 0, patterns = 0;
            cards.forEach(card => {{
                const category = card.dataset.category || '';
                const status = card.dataset.status || '';
                if (selectedCategory === 'all' || category === selectedCategory) {{
                    total++;
                    if (status === 'violation') violations++;
                    if (status === 'adherence') adherences++;
                    if (status === 'pattern') patterns++;
                }}
            }});
            document.getElementById('statusCountAll').textContent = total;
            document.getElementById('statusCountViolation').textContent = violations;
            document.getElementById('statusCountAdherence').textContent = adherences;
            document.getElementById('statusCountPattern').textContent = patterns;
        }}

        function filterCards() {{
            const query = searchInput.value.toLowerCase();
            let visibleCount = 0;

            cards.forEach(card => {{
                const text = card.textContent.toLowerCase();
                const pattern = card.dataset.pattern || '';
                const category = card.dataset.category || '';
                const target = card.dataset.target || '';
                const status = card.dataset.status || '';

                const matchesCategory = (selectedCategory === 'all' || category === selectedCategory);
                const matchesStatus = (selectedStatus === 'all' || status === selectedStatus);
                const matchesSearch = (!query || text.includes(query) || pattern.includes(query) || category.includes(query) || target.includes(query));

                if (matchesCategory && matchesStatus && matchesSearch) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            if (selectedStatus === 'violation' && visibleCount === 0) {{
                noViolationsAlert.style.display = 'flex';
                noResultsMessage.style.display = 'none';
            }} else if (visibleCount === 0) {{
                noViolationsAlert.style.display = 'none';
                noResultsMessage.style.display = 'block';
            }} else {{
                noViolationsAlert.style.display = 'none';
                noResultsMessage.style.display = 'none';
            }}
        }}

        searchInput.addEventListener('input', filterCards);

        categoryBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                categoryBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedCategory = btn.dataset.filter;
                updateStatusCounts();
                filterCards();
            }});
        }});

        statusBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                statusBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedStatus = btn.dataset.status;
                filterCards();
            }});
        }});

        function copyArchMapForLlm() {{
            const rawText = document.getElementById('llmArchMapRaw').value;
            const btn = document.getElementById('copyLlmBtn');
            const originalHtml = btn.innerHTML;

            function showSuccess() {{
                btn.innerHTML = '<i class="check icon"></i> Copied to Clipboard!';
                btn.classList.remove('purple');
                btn.classList.add('green');

                const toast = document.getElementById('copyToast');
                if (toast) {{
                    toast.style.display = 'block';
                    setTimeout(() => {{ toast.style.display = 'none'; }}, 4000);
                }}

                setTimeout(() => {{
                    btn.innerHTML = originalHtml;
                    btn.classList.remove('green');
                    btn.classList.add('purple');
                }}, 2500);
            }}

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(rawText).then(showSuccess).catch(err => {{
                    fallbackCopy(rawText, showSuccess);
                }});
            }} else {{
                fallbackCopy(rawText, showSuccess);
            }}
        }}

        function fallbackCopy(text, callback) {{
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand('copy');
                callback();
            }} catch (e) {{
                console.error('Fallback copy failed', e);
            }}
            document.body.removeChild(textarea);
        }}

        function toggleArchMapPreview() {{
            const container = document.getElementById('archMapPreviewContainer');
            const btnText = document.getElementById('toggleArchMapText');
            if (container.style.display === 'none') {{
                container.style.display = 'block';
                btnText.textContent = 'Hide Map Preview';
            }} else {{
                container.style.display = 'none';
                btnText.textContent = 'View Map Preview';
            }}
        }}

        updateStatusCounts();
    </script>
</body>
</html>
"""


class HtmlReportFormatter(ReportFormatterPort):
    """Renders a standalone, responsive, interactive Semantic UI (Fomantic-UI) HTML dashboard for DetectionReport."""

    def format(self, report: DetectionReport, verbose: bool = False) -> str:
        counts = self._calculate_status_counts(report.detections)
        cards_html = "".join(self._render_cards_list(report.detections))
        category_filters = "".join(self._render_category_filters(report))
        project_name = self._resolve_project_name(report.project_path)
        llm_arch_map = self._build_llm_architectural_map(report, counts, project_name)

        return _HTML_DASHBOARD_TEMPLATE.format(
            project_name=project_name,
            total_detections=report.total_detections_count,
            total_violations=counts["violation"],
            total_adherences=counts["adherence"],
            total_patterns=counts["pattern"],
            scanned_files=report.scanned_files_count,
            elapsed_seconds=f"{report.elapsed_seconds:.3f}",
            category_filters=category_filters,
            cards_html=cards_html,
            llm_arch_map_preview=html.escape(llm_arch_map),
            llm_arch_map_raw=html.escape(llm_arch_map),
        )

    def _build_llm_architectural_map(
        self, report: DetectionReport, counts: dict[str, int], project_name: str
    ) -> str:
        """Constructs structured, token-efficient Markdown prompt for LLM architecture analysis."""
        lines = [
            "# 🏛️ Codebase Architecture Map & Refactoring Analysis",
            "",
            "## 📌 Project Overview",
            f"- **Target Project:** `{project_name}`",
            f"- **Files Scanned:** `{report.scanned_files_count}`",
            f"- **Total Architecture Findings:** `{report.total_detections_count}`",
            f"- **⚠️ Violations / Code Smells (Action Required):** `{counts.get('violation', 0)}`",
            f"- **🔷 Design Patterns Identified:** `{counts.get('pattern', 0)}`",
            f"- **✅ SOLID & Clean Code Adherences:** `{counts.get('adherence', 0)}`",
            "",
            "---",
            "",
            "## 🎯 Task for AI / LLM Architect",
            "> **Prompt Instructions:**",
            "> 1. **Analyze Modularity & Coupling:** Review the package breakdown, design pattern distribution, and high-coupling components.",
            "> 2. **Prioritize Top Architectural Violations:** Review the listed code smells (KISS complexity, Law of Demeter, Fan-Out, God Objects, etc.) and highlight the top 3-5 highest-risk issues.",
            "> 3. **Provide Concrete Refactoring Suggestions:** For each top issue, propose architectural patterns (e.g. Strategy, Facade, Composite, Observer) and provide concise Python code examples/signatures.",
            "> 4. **SOLID Improvements:** Explain how to resolve the identified Open-Closed, Liskov, and Demeter issues without over-engineering.",
            "",
            "---",
        ]

        patterns_by_type: dict[str, list[Any]] = {}
        violations_by_type: dict[str, list[Any]] = {}
        adherences_by_type: dict[str, list[Any]] = {}
        file_to_findings: dict[str, list[str]] = {}

        for d in report.detections:
            status = self._classify_detection_status(d)
            ptype = d.pattern_type.value.upper()
            if status == "pattern":
                patterns_by_type.setdefault(ptype, []).append(d)
            elif status == "violation":
                violations_by_type.setdefault(ptype, []).append(d)
            else:
                adherences_by_type.setdefault(ptype, []).append(d)

            loc_file = d.primary_location.file_path if d.primary_location and d.primary_location.file_path else "unknown"
            short_file = loc_file.replace("\\", "/").split("/")[-1]
            file_to_findings.setdefault(short_file, []).append(f"{ptype} ({status})")

        # 1. Design Patterns
        lines.append(f"## 🔷 Active Design Patterns ({counts.get('pattern', 0)} instances)")
        if patterns_by_type:
            for ptype, items in sorted(patterns_by_type.items()):
                lines.append(f"### Pattern: `{ptype}` ({len(items)} instances)")
                for d in items:
                    loc = f"{d.primary_location.file_path}:{d.primary_location.line}" if d.primary_location else ""
                    loc_str = f" in `{loc}`" if loc else ""
                    lines.append(f"- **{d.target_name}** ({d.target_kind}, confidence {d.confidence.percentage_str}){loc_str}")
                    lines.append(f"  - *Summary:* {d.summary}")
            lines.append("")
        else:
            lines.append("*No design patterns identified.*\n")

        lines.append("---")
        lines.append("")

        # 2. Violations & Code Smells
        lines.append(f"## ⚠️ Architectural Violations & Code Smells ({counts.get('violation', 0)} instances)")
        if violations_by_type:
            for vtype, items in sorted(violations_by_type.items()):
                lines.append(f"### Violation: `{vtype}` ({len(items)} occurrences)")
                for d in items[:30]:
                    loc = f"{d.primary_location.file_path}:{d.primary_location.line}" if d.primary_location else ""
                    loc_str = f" in `{loc}`" if loc else ""
                    lines.append(f"- **{d.target_name}** ({d.confidence.percentage_str}){loc_str}")
                    lines.append(f"  - *Risk / Smell:* {d.summary}")
                    for ev in d.evidences[:2]:
                        lines.append(f"  - *Evidence:* `+{int(ev.weight * 100)}%` [{ev.rule_code}] {ev.description}")
                if len(items) > 30:
                    lines.append(f"  *(... and {len(items) - 30} more {vtype} occurrences)*")
            lines.append("")
        else:
            lines.append("✅ *Zero violations detected! All evaluated code adheres to clean architecture principles.*\n")

        lines.append("---")
        lines.append("")

        # 3. Clean Adherences
        lines.append(f"## ✅ SOLID Principles & Clean Adherences ({counts.get('adherence', 0)} instances)")
        if adherences_by_type:
            for atype, items in sorted(adherences_by_type.items()):
                lines.append(f"### Principle: `{atype}` ({len(items)} instances)")
                for d in items[:25]:
                    loc = f"{d.primary_location.file_path}:{d.primary_location.line}" if d.primary_location else ""
                    loc_str = f" in `{loc}`" if loc else ""
                    lines.append(f"- **{d.target_name}** ({d.confidence.percentage_str}){loc_str} - {d.summary}")
            lines.append("")
        else:
            lines.append("*None recorded.*\n")

        lines.append("---")
        lines.append("")

        # 4. Module & File Hotspots Distribution
        lines.append("## 🗺️ Module & File Hotspots Distribution")
        top_files = sorted(file_to_findings.items(), key=lambda x: len(x[1]), reverse=True)[:25]
        if top_files:
            for fname, f_items in top_files:
                p_count = sum(1 for x in f_items if "pattern" in x)
                v_count = sum(1 for x in f_items if "violation" in x)
                a_count = sum(1 for x in f_items if "adherence" in x)
                lines.append(f"- **`{fname}`**: {len(f_items)} findings ({v_count} violations, {p_count} patterns, {a_count} adherences)")
        lines.append("")

        return "\n".join(lines)

    def _calculate_status_counts(self, detections: list[Any]) -> dict[str, int]:
        counts = {"violation": 0, "adherence": 0, "pattern": 0}
        for d in detections:
            status = self._classify_detection_status(d)
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _resolve_project_name(self, project_path: str | None) -> str:
        if not project_path:
            return "Codebase"
        return html.escape(project_path)

    @classmethod
    def _is_violation_target(cls, kind: str, summary: str) -> bool:
        for term in _VIOLATION_TERMS:
            if term in kind:
                return True
        for phrase in _VIOLATION_SUMMARY_SUBSTRINGS:
            if phrase in summary:
                return True
        return False

    @classmethod
    def _has_violation_evidence(cls, evidences: list[Any]) -> bool:
        for ev in evidences:
            code = getattr(ev, "rule_code", "").upper()
            if code.endswith(_VIOLATION_RULE_SUFFIXES):
                return True
        return False

    @classmethod
    def _is_adherence_target(cls, kind: str, summary: str, cat: Any) -> bool:
        if "adherence" in summary or "polymorphic_hierarchy" in kind or "segregated_role_interface" in kind:
            return True
        return cat == PatternCategory.PRINCIPLE

    @classmethod
    def _classify_detection_status(cls, det: Any) -> str:
        """Classifies detection as 'violation' (needs fix), 'adherence' (clean practice), or 'pattern'."""
        kind = getattr(det, "target_kind", "").lower()
        summary = getattr(det, "summary", "").lower()
        if cls._is_violation_target(kind, summary):
            return "violation"
        if cls._has_violation_evidence(getattr(det, "evidences", [])):
            return "violation"
        if cls._is_adherence_target(kind, summary, getattr(det, "pattern_category", None)):
            return "adherence"
        return "pattern"

    @classmethod
    def _get_status_card_theme(cls, status: str, cat_style: dict[str, str]) -> tuple[str, str, str]:
        if status == "violation":
            badge = '<span class="ui mini red label" style="font-weight: 700;"><i class="exclamation triangle icon"></i> ACTION REQUIRED (VIOLATION)</span>'
            banner = '<div class="ui mini negative message" style="padding: 8px 12px; margin-bottom: 12px; background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.35); color: #fca5a5;"><i class="warning sign icon"></i> <strong>Anti-Pattern / Violation:</strong> Refactoring recommended to resolve this code smell.</div>'
            return badge, banner, "#f43f5e"
        if status == "adherence":
            badge = '<span class="ui mini green label" style="font-weight: 700;"><i class="check circle icon"></i> GOOD PRACTICE (ADHERENCE)</span>'
            banner = '<div class="ui mini positive message" style="padding: 8px 12px; margin-bottom: 12px; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); color: #86efac;"><i class="check circle outline icon"></i> <strong>SOLID Adherence:</strong> Code adheres cleanly to architectural principles (No fix required).</div>'
            return badge, banner, "#10b981"
        badge = (
            '<span class="ui mini blue label" style="font-weight: 700;"><i class="cube icon"></i> DESIGN PATTERN</span>'
        )
        return badge, "", cat_style["accent"]

    def _render_detection_card(self, idx: int, det: Any) -> str:
        cat_style = CATEGORY_STYLES.get(
            det.pattern_category,
            {
                "text": "#94a3b8",
                "bg": "#1e293b44",
                "border": "#475569",
                "accent": "#64748b",
                "label_color": "grey",
                "icon": "tag",
                "name": "Other",
            },
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

        status = self._classify_detection_status(det)
        status_badge, status_banner, card_border = self._get_status_card_theme(status, cat_style)

        evidences_html = self._render_evidences_html(det, cat_style)
        related_html = self._render_related_locations_html(det)

        return f"""
        <div class="ui fluid inverted card pattern-card" data-pattern="{html.escape(det.pattern_type.value)}" data-category="{html.escape(det.pattern_category.value)}" data-status="{status}" data-target="{html.escape(det.target_name)}" style="background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid {card_border} !important; margin-bottom: 14px;">
            <div class="content" style="border-bottom: 1px solid #1e293b; padding: 12px 16px;">
                <div class="right floated" style="display: flex; align-items: center; gap: 6px;">
                    {status_badge}
                    <span class="ui mini {badge_color} label" style="font-weight: 700;">{det.confidence.percentage_str} [{det.level.value}]</span>
                </div>
                <div class="header" style="color: #f8fafc; font-size: 15px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="color: #64748b; font-weight: 700; font-size: 13px;">#{idx}</span>
                    <span class="ui mini {cat_style["label_color"]} label"><i class="{cat_style["icon"]} icon"></i> {html.escape(cat_style["name"].upper())}</span>
                    <span class="ui mini {pat_style["label"]} label">{html.escape(det.pattern_type.value.upper())}</span>
                    <span style="color: #cbd5e1; font-weight: 600;">{html.escape(det.target_kind)}:</span>
                    <span style="color: #38bdf8; font-family: monospace; font-weight: 700;">{html.escape(det.target_name)}</span>
                </div>
            </div>
            <div class="content" style="padding: 14px 16px; font-size: 13px;">
                {status_banner}
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
                        {evidences_html}
                    </div>
                </div>
                {related_html}
            </div>
        </div>
        """

    def _render_evidences_html(self, det: Any, cat_style: dict[str, str]) -> str:
        evidences_html = []
        for ev in det.evidences:
            pct = int(ev.weight * 100)
            loc_str = (
                f'<span class="location-tag"><i class="map marker alternate icon"></i> {html.escape(str(ev.location))}</span>'
                if ev.location
                else ""
            )
            evidences_html.append(
                f'<div class="item" style="padding: 4px 0; border-left: 3px solid {cat_style["accent"]}; padding-left: 10px; margin-bottom: 4px;">'
                f'<span class="weight-tag" style="color: {cat_style["text"]}; font-weight: 700; font-family: monospace;">+{pct}%</span> '
                f'<span class="rule-code" style="color: #94a3b8; font-family: monospace; font-size: 11px;">[{html.escape(ev.rule_code)}]</span> '
                f'<span style="color: #e2e8f0;">{html.escape(ev.description)}</span> {loc_str}'
                f"</div>"
            )
        return "".join(evidences_html)

    def _render_related_locations_html(self, det: Any) -> str:
        if not det.related_locations:
            return ""
        rel_items = " ".join(
            f'<span class="code-pill"><i class="file code outline icon"></i> {html.escape(str(loc))}</span>'
            for loc in det.related_locations
        )
        return f'<div style="margin-top: 10px; font-size: 12px; color: #94a3b8;"><strong>Related Locations:</strong><div style="margin-top: 4px;">{rel_items}</div></div>'

    def _render_category_filters(self, report: DetectionReport) -> list[str]:
        category_filters = []
        for cat_enum, style in CATEGORY_STYLES.items():
            count = report.summary_by_category.get(cat_enum.value, 0)
            if count > 0:
                category_filters.append(
                    f"""
                    <a class="item cat-filter-btn" data-filter="{cat_enum.value}">
                        <i class="{style["icon"]} icon" style="color: {style["accent"]};"></i>
                        {style["name"]}
                        <div class="ui mini {style["label_color"]} label">{count}</div>
                    </a>
                    """
                )
        return category_filters

    def _count_confidence_levels(self, detections: list[Any]) -> dict[ConfidenceLevel, int]:
        counts: dict[ConfidenceLevel, int] = {level: 0 for level in ConfidenceLevel}
        for d in detections:
            counts[d.level] += 1
        return counts

    def _render_cards_list(self, detections: list[Any]) -> list[str]:
        cards: list[str] = []
        for idx, det in enumerate(detections, 1):
            cards.append(self._render_detection_card(idx, det))
        return cards
