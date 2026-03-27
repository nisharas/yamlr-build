"""
Yamlr EVIDENCE AGGREGATOR
--------------------------
Consolidates signed evidence receipts into authoritative reports.

Why: Aggregates distributed evidence across multiple scan/heal sessions 
     into single, verifiable compliance documents.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from yamlr.pro.compliance.evidence import EvidenceEngine
from yamlr.pro.compliance.ruleset import ComplianceRegistry
from yamlr.core.utils import xml_escape

logger = logging.getLogger("yamlr.pro.compliance.aggregator")
__all__ = ['EvidenceAggregator']


class EvidenceAggregator:
    """
    Consolidates Yamlr DNA-signed evidence receipts into auditor-ready PDF and JSON reports.
    """

    def __init__(self, evidence_dir: str):
        self.evidence_dir = Path(evidence_dir)
        self.engine = EvidenceEngine()
        self.receipts: List[Dict[str, Any]] = []
        self.tampered_files: List[str] = []
        
    def load_and_verify(self, use_parallel: bool = True) -> bool:
        """
        Scans the evidence directory, loads all receipts, and cryptographically verifies them.
        Returns True if all receipts are valid, False if tampering is detected.
        
        Why: Parallell verification [PHASE-19] ensures sub-second aggregation 
             even for thousands of signed receipts.
        """
        if not self.evidence_dir.exists() or not self.evidence_dir.is_dir():
            logger.error(f"Evidence directory {self.evidence_dir} does not exist.")
            return False
            
        receipt_paths = list(self.evidence_dir.glob("evidence-*.json"))
        if not receipt_paths:
            return True

        is_clean = True
        
        if use_parallel and len(receipt_paths) > 5:
            from concurrent.futures import ProcessPoolExecutor
            # ProcessPool is preferred for CPU-bound hashing
            with ProcessPoolExecutor() as executor:
                # We need a helper because we can't pickle self.engine easily if it's complex
                results = list(executor.map(_verify_single_receipt_path, [str(p) for p in receipt_paths]))
                
            for receipt, valid, filename in results:
                if receipt is None: continue
                if not valid:
                    self.tampered_files.append(filename)
                    is_clean = False
                else:
                    self.receipts.append(receipt)
        else:
            # Sequential fallback
            for file_path in receipt_paths:
                res = _verify_single_receipt_path(str(file_path))
                receipt, valid, filename = res
                if receipt is None: continue
                if not valid:
                    self.tampered_files.append(filename)
                    is_clean = False
                else:
                    self.receipts.append(receipt)
                
        return is_clean

    def fast_metadata_extract(self) -> Dict[str, Any]:
        """
        Peeks at evidence receipts to pull summary stats without full crypto verification.
        
        Why: High-speed path for 'yamlr status' and ROI dashboards.
        """
        summary = {"total_receipts": 0, "total_remediations": 0, "last_updated": 0.0}
        for file_path in self.evidence_dir.glob("evidence-*.json"):
            try:
                # We only parse the file once to get stats
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    payload = data.get("payload", {})
                    summary["total_receipts"] += 1
                    summary["total_remediations"] += len(payload.get("remediations", []))
                    mtime = os.path.getmtime(file_path)
                    if mtime > summary["last_updated"]:
                        summary["last_updated"] = mtime
            except Exception:
                continue
        return summary

def _verify_single_receipt_path(path: str) -> tuple[Optional[Dict], bool, str]:
    """Helper for parallel verification to avoid pickling issues."""
    from yamlr.pro.compliance.evidence import EvidenceEngine
    import json
    import os
    
    filename = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
            
        if "signature" not in receipt or "payload" not in receipt:
            return None, False, filename
            
        engine = EvidenceEngine()
        is_valid = engine.verify_receipt(receipt)
        return receipt, is_valid, filename
    except Exception:
        return None, False, filename

    def aggregate_findings(self) -> Dict[str, Dict[str, Any]]:
        """
        Groups all cryptographically verified findings by Compliance Control (SOC2, CIS, HIPAA).
        """
        # compliance_map structure: 
        # { 
        #   "SOC2: CC6.1": { "description": "...", "incidents": [{"file": "pod.yaml", "rule": "x"}] } 
        # }
        compliance_map: Dict[str, Dict[str, Any]] = {}
        
        for receipt in self.receipts:
            payload = receipt["payload"]
            file_name = payload.get("file_path", "unknown")
            findings = payload.get("remediations", [])
            
            for finding in findings:
                rule_id = finding.get("rule_id")
                if not rule_id:
                    continue
                    
                # Fetch attributions natively mapped in ruleset.py
                attributions = ComplianceRegistry.get_attributions(rule_id)
                control_meta = ComplianceRegistry.get_controls_for_rule(rule_id)
                description = control_meta.description if control_meta else "Security Posture Remediation"
                
                # Assign this file to every mapped control (e.g., SOC2, CIS)
                for tag in attributions:
                    if tag not in compliance_map:
                        compliance_map[tag] = {
                            "description": description,
                            "incidents": []
                        }
                    compliance_map[tag]["incidents"].append({
                        "file": file_name,
                        "rule_id": rule_id,
                        "severity": finding.get("severity", "UNKNOWN"),
                        "timestamp": payload.get("timestamp")
                    })
                    
        return compliance_map

    def extract_json(self) -> str:
        """Exports the aggregated compliance map as a structured JSON string.
        
        Why: Enables programmatic consumption of compliance data by 
             external GRC (Governance, Risk, and Compliance) systems.
        """
        summary = {
            "metadata": {
                "generated": datetime.now(timezone.utc).isoformat() + "Z",
                "total_receipts_verified": len(self.receipts),
                "tampered_receipts_detected": len(self.tampered_files),
                "tampered_files": self.tampered_files
            },
            "controls": self.aggregate_findings()
        }
        return json.dumps(summary, indent=2)

    def extract_pdf(self, output_path: str) -> str:
        """
        Exports the aggregated compliance map as an Auditor-Ready PDF.
        Requires 'reportlab' dependency.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            raise ImportError("The 'reportlab' package is required for PDF export. Run 'pip install reportlab'")

        doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        Title = styles["Title"]
        Heading1 = styles["Heading1"]
        Heading2 = styles["Heading2"]
        Normal = styles["Normal"]
        
        # Determine overall integrity
        if len(self.tampered_files) > 0:
            status_color = colors.red
            status_text = "FAILED (Tampering Detected)"
        else:
            status_color = colors.green
            status_text = "VERIFIED (Cryptographically Sound)"

        elements = []

        # Title / Header
        elements.append(Paragraph("Yamlr Enterprise (Pro) Compliance Report", Title))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", Normal))
        elements.append(Paragraph(f"<b>Receipts Audited:</b> {len(self.receipts)}", Normal))
        elements.append(Paragraph(f"<b>Integrity Verification:</b> <font color='{status_color.hexval()}'><b>{xml_escape(status_text)}</b></font>", Normal))
        elements.append(Spacer(1, 24))

        if self.tampered_files:
            elements.append(Paragraph("TAMPERED RECEIPTS DETECTED", Heading1))
            for f in self.tampered_files:
                elements.append(Paragraph(f"• {xml_escape(f)}", Normal))
            elements.append(Spacer(1, 24))

        # Compliance Breakdown
        elements.append(Paragraph("Compliance Controls Satisfied", Heading1))
        elements.append(Spacer(1, 12))

        compliance_map = self.aggregate_findings()

        if not compliance_map:
            elements.append(Paragraph("No specific compliance controls were engaged during this batch run.", Normal))
        else:
            for tag, details in sorted(compliance_map.items()):
                elements.append(Paragraph(f"<b>{xml_escape(tag)}</b> - {xml_escape(details['description'])}", Heading2))
                elements.append(Spacer(1, 6))
                
                # Render table of incidents
                data = [["File", "Rule Interpolated", "Severity"]]
                for inc in details["incidents"]:
                    data.append([xml_escape(inc["file"]), xml_escape(inc["rule_id"]), xml_escape(inc["severity"])])
                    
                t = Table(data, colWidths=[200, 150, 100])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                    ('GRID', (0,0), (-1,-1), 1, colors.black)
                ]))
                
                elements.append(t)
                elements.append(Spacer(1, 16))

        doc.build(elements)
        return output_path
