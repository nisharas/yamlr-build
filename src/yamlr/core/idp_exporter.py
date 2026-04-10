from __future__ import annotations

import json
import time

from yamlr.core.scoring import AppSafetyReport

__all__ = ["IDPExporter"]


class IDPExporter:
    """Exports AppSafetyReport into various platform formats.

    Why: To enable seamless integration into existing "Source of Truth" portals
         (Backstage, Grafana, Port) without owning the dashboard.
    """

    def __init__(self, report: AppSafetyReport):
        self.report = report

    def export_backstage(self) -> str:
        """Emits a JSON array suitable for Backstage component safety annotations.

        Why: Backstage usually requires a JSON file or sidecar data for
             entity-specific health metrics.
        """
        components = []
        for app in self.report.apps:
            status = "healthy"
            if app.score < 50:
                status = "critical"
            elif app.score < 80:
                status = "warning"

            components.append(
                {
                    "component": app.app_name,
                    "metadata": {
                        "annotations": {
                            "yamlr.dev/safety-score": f"{app.score:.1f}",
                            "yamlr.dev/top-risks": ", ".join(app.top_categories),
                            "yamlr.dev/rule-violations": ", ".join(app.top_rules),
                            "yamlr.dev/last-updated": str(int(time.time())),
                            "yamlr.dev/scoring-version": str(self.report.scoring_version),
                        }
                    },
                    "status": status,
                }
            )
        return json.dumps(components, indent=2)

    def export_prometheus(self) -> str:
        """Emits OpenMetrics/Prometheus text format.

        Why: Enables alerting and historical dashboards (Grafana) via existing infra.
        """
        lines = [
            "# HELP yamlr_app_safety_score The calculated health and safety score for the application.",
            "# TYPE yamlr_app_safety_score gauge",
        ]

        for app in self.report.apps:
            lines.append(f'yamlr_app_safety_score{{app="{app.app_name}"}} {app.score:.1f}')

            # Export categories as individual metrics for drill-down
            for cat in app.top_categories:
                safe_cat = cat.lower().replace(" ", "_")
                lines.append(f'yamlr_app_violation_category_present{{app="{app.app_name}", category="{safe_cat}"}} 1')

        lines.append(f"yamlr_global_safety_score {self.report.overall_score:.1f}")
        lines.append(f"yamlr_scoring_version {self.report.scoring_version}")

        return "\n".join(lines)

    def export_port(self) -> str:
        """Emits a JSON object for GetPort.io entity ingestion.

        Why: Port is the leading internal developer portal for modern K8s teams.
        """
        entities = []
        for app in self.report.apps:
            entities.append(
                {
                    "identifier": app.app_name,
                    "title": f"Yamlr Safety: {app.app_name}",
                    "blueprint": "kubernetes_service",  # Customizable target
                    "properties": {
                        "yamlr_score": app.score,
                        "yamlr_status": "healthy" if app.score > 80 else "at_risk",
                        "top_violations": app.top_rules,
                        "last_scan_at": int(time.time()),
                    },
                }
            )
        return json.dumps(entities, indent=2)

    def export_pagerduty(self) -> str:
        """Emits a JSON payload for PagerDuty Change Events or Alerts.

        Why: Enables automated incident response if a manifest's safety
             score drops below a critical threshold in CI.
        """
        critical_apps = [a for a in self.report.apps if a.score < 50]
        if not critical_apps:
            return json.dumps({"status": "no_incident", "message": "All apps are healthy."})

        return json.dumps(
            {
                "payload": {
                    "summary": f"Yamlr Enterprise: {len(critical_apps)} applications have critical safety violations.",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "severity": "critical",
                    "source": "yamlr-engine",
                    "component": "k8s-manifests",
                    "group": "security",
                    "class": "compliance-violation",
                    "custom_details": {
                        "apps": [a.app_name for a in critical_apps],
                        "scores": {a.app_name: a.score for a in critical_apps},
                        "overall_score": self.report.overall_score,
                        "details": [
                            {
                                "app": a.app_name,
                                "violations": [
                                    f"{f['rule_id']} (Line {f['line']}): {f['message']}"
                                    for f in a.detailed_findings[:5]
                                ],
                            }
                            for a in critical_apps
                        ],
                    },
                },
                "routing_key": "YOUR_ROUTING_KEY_HERE",  # Placeholder for user
                "event_action": "trigger",
            },
            indent=2,
        )

    def export_json(self) -> str:
        """Emits the raw internal Safety Spec with Pydantic compatibility."""
        # Pydantic V2 model_dump_json vs V1 json()
        if hasattr(self.report, "model_dump_json"):
            return self.report.model_dump_json(indent=2)
        return self.report.json(indent=2)
