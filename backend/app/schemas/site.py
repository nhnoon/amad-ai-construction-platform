from pydantic import BaseModel
from typing import Optional


class SiteReportOut(BaseModel):
    id: int
    project_id: int
    report_date: str
    weather: str
    summary: str

    model_config = {"from_attributes": True}


class DailyActivityOut(BaseModel):
    id: int
    project_id: int
    subcontractor_id: int
    site_report_id: int
    activity_date: str
    activity_description: str
    manpower_count: int

    model_config = {"from_attributes": True}
