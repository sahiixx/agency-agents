"""
FirstCall pipeline: capture -> qualify -> geo-match -> schedule -> report
Consumes REA rebuild signals (e.g. bayut_teardown clusters).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict


class FirstCallPipeline:
    def __init__(self):
        self.leads: list = []
        self.deals: list = []

    async def capture(self, source: str, geo: Dict, count: int, analysis_id: str) -> Dict:
        lead = {
            "id": f"lead_{analysis_id}_{len(self.leads)}",
            "source": source,
            "geo": geo,
            "count": count,
            "analysis_id": analysis_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "status": "captured",
        }
        self.leads.append(lead)
        return lead

    async def qualify(self, lead: Dict) -> Dict:
        score = 0.0
        if lead.get("count", 0) >= 3:
            score += 0.5
        if lead.get("source") == "bayut_teardown":
            score += 0.3
        lat = lead.get("geo", {}).get("lat", 0)
        if 25.0 < lat < 25.4:
            score += 0.2
        lead["score"] = min(1.0, score)
        lead["qualified"] = score >= 0.7
        lead["status"] = "qualified" if lead["qualified"] else "disqualified"
        return lead

    async def geo_match(self, lead: Dict) -> Dict:
        lat = lead.get("geo", {}).get("lat", 0)
        lng = lead.get("geo", {}).get("lng", 0)
        if lat > 25.2 and lng > 55.27:
            area = "Downtown Dubai"
        elif lat > 25.18 and lng < 55.2:
            area = "Dubai Marina"
        else:
            area = "Dubai"
        lead["area"] = area
        lead["geo_matched"] = True
        lead["status"] = "geo_matched"
        return lead

    async def schedule(self, lead: Dict) -> Dict:
        if not lead.get("qualified"):
            lead["status"] = "skipped"
            return lead
        lead["scheduled"] = {
            "channel": "WhatsApp",
            "tool": "schedule_viewing",
            "time": datetime.now(timezone.utc).isoformat(),
        }
        lead["status"] = "scheduled"
        return lead

    async def report(self, lead: Dict) -> Dict:
        if lead.get("qualified"):
            self.deals.append(lead)
        return {
            "lead_id": lead["id"],
            "source": lead.get("source"),
            "area": lead.get("area"),
            "score": lead.get("score"),
            "status": lead.get("status"),
            "pipeline": "capture -> qualify -> geo-match -> schedule -> report",
        }

    async def run_pipeline(
        self, source: str, geo: Dict, count: int, analysis_id: str
    ) -> Dict:
        lead = await self.capture(source, geo, count, analysis_id)
        lead = await self.qualify(lead)
        lead = await self.geo_match(lead)
        lead = await self.schedule(lead)
        return await self.report(lead)


pipeline = FirstCallPipeline()
