"""
graph-sight for REA: trust scores + evidence-based function recovery.
"""

from __future__ import annotations

from typing import Dict, List


class GraphSightREA:
    def calculate_trust_score(self, evidence: Dict) -> float:
        confidence = float(evidence.get("confidence", 0) or 0)
        categories = evidence.get("references") or evidence.get("categories") or []
        score = confidence
        if any(c in ("DUBAI_RE", "BAYUT") for c in categories):
            score += 0.1
        if evidence.get("type") == "entropy" and float(evidence.get("value", 0) or 0) > 7.2:
            score -= 0.2
        return min(1.0, max(0.0, round(score, 3)))

    def ast_context_for_function(self, func_name: str, evidence: List[Dict]) -> Dict:
        has_cluster = any("cluster" in str(e.get("value", "")).lower() for e in evidence)
        has_grid = any(
            "gridsize" in str(e.get("value", "")).lower() or "grid" in str(e.get("value", "")).lower()
            for e in evidence
        )
        if has_cluster and has_grid:
            return {
                "original": func_name,
                "recovered": "clusterProperties",
                "args": [
                    {"name": "properties", "type": "Property[]"},
                    {"name": "mapBounds", "type": "Bounds"},
                    {"name": "zoom", "type": "number"},
                ],
                "returns": {"type": "Cluster[]"},
                "trust": 0.88,
                "evidence_map": {
                    f"0x{int(e.get('offset', 0)):x}": str(e.get("value", ""))[:50]
                    for e in evidence[:5]
                },
            }
        return {
            "original": func_name,
            "recovered": "reconstructedFeature",
            "args": [],
            "returns": {"type": "unknown"},
            "trust": 0.5,
            "evidence_map": {},
        }


graph_sight = GraphSightREA()
