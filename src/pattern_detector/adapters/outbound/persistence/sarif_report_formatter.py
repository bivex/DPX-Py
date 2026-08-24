"""SARIF v2.1.0 Report Formatter for GitHub Actions Code Scanning integration."""

from __future__ import annotations

import json
from typing import Any

from pattern_detector.domain.detection import DetectionReport
from pattern_detector.domain.value_objects import ConfidenceLevel, PatternCategory


class SarifReportFormatter:
    """Formats DetectionReport into standard OASIS SARIF v2.1.0 JSON format."""

    def format(self, report: DetectionReport, verbose: bool = False) -> str:
        """Serialize DetectionReport to SARIF JSON string."""
        rule_map: dict[str, dict[str, Any]] = {}
        results: list[dict[str, Any]] = []

        for d in report.detections:
            rule_id = f"DPX-{d.pattern_type.value.upper()}"
            if rule_id not in rule_map:
                rule_map[rule_id] = {
                    "id": rule_id,
                    "name": d.pattern_type.value.replace("_", " ").title().replace(" ", ""),
                    "shortDescription": {
                        "text": f"{d.pattern_category.value.title()} pattern / rule: {d.pattern_type.value.replace('_', ' ').title()}"
                    },
                    "fullDescription": {
                        "text": f"Detects instances and adherence/violations of {d.pattern_type.value.upper()}."
                    },
                    "defaultConfiguration": {"level": self._map_level(d.pattern_category, d.confidence.level)},
                    "properties": {
                        "category": d.pattern_category.value,
                        "tags": [d.pattern_category.value, "architecture", "solid", "gof-pattern"],
                    },
                }

            loc = d.primary_location
            file_uri = loc.file_path if loc and loc.file_path else "unknown"
            start_line = max(1, loc.line) if loc else 1

            # Build result object
            result: dict[str, Any] = {
                "ruleId": rule_id,
                "level": self._map_level(d.pattern_category, d.confidence.level),
                "message": {"text": f"[{d.confidence.percentage_str}] {d.summary}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": file_uri,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": start_line,
                                "startColumn": 1,
                            },
                        }
                    }
                ],
                "properties": {
                    "confidence": d.confidence.score,
                    "confidenceLevel": d.confidence.level.value,
                    "targetName": d.target_name,
                    "targetKind": d.target_kind,
                },
            }

            if d.evidences:
                result["codeFlows"] = [
                    {
                        "threadFlows": [
                            {
                                "locations": [
                                    {
                                        "location": {
                                            "message": {"text": ev.description},
                                            "physicalLocation": {
                                                "artifactLocation": {
                                                    "uri": ev.location.file_path
                                                    if ev.location and ev.location.file_path
                                                    else file_uri
                                                },
                                                "region": {
                                                    "startLine": max(1, ev.location.line) if ev.location else start_line
                                                },
                                            },
                                        }
                                    }
                                    for ev in d.evidences
                                ]
                            }
                        ]
                    }
                ]

            results.append(result)

        sarif_obj = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "DPX-Py",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/bivex/DPX-Py",
                            "rules": list(rule_map.values()),
                        }
                    },
                    "results": results,
                }
            ],
        }

        return json.dumps(sarif_obj, indent=2)

    @staticmethod
    def _map_level(category: PatternCategory, confidence: ConfidenceLevel) -> str:
        if category == PatternCategory.PRINCIPLE:
            return "error" if confidence in (ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH) else "warning"
        if category == PatternCategory.ARCHITECTURAL:
            return "warning"
        return "note"
