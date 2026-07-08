from pydantic import BaseModel
from typing import Optional


class SiteReportOut(BaseModel):
    id: int
    project_id: int
    report_date: str
    weather: str
    summary: str

    model_config = {"from_attributes": True}


class SiteReportCardOut(BaseModel):
    report_id: int
    project_id: int
    project_name: str
    report_date: str
    engineer: Optional[str] = None
    weather: str
    work_progress: str
    risk_indicator: str
    safety_indicator: str
    quality_indicator: str


class DailyActivityOut(BaseModel):
    id: int
    project_id: int
    subcontractor_id: int
    site_report_id: int
    activity_date: str
    activity_description: str
    manpower_count: int

    model_config = {"from_attributes": True}


class ReportEngineerOut(BaseModel):
    id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_on_project: Optional[str] = None


class ReportManpowerBySubcontractorOut(BaseModel):
    subcontractor_id: int
    subcontractor_name: str
    workers: int
    activity_count: int


class ReportManpowerOut(BaseModel):
    total_workers: int
    subcontractor_breakdown: list[ReportManpowerBySubcontractorOut]


class ReportAttachmentOut(BaseModel):
    source_type: str
    source_id: int
    title: str
    date: Optional[str] = None


class ReportDocumentReferenceOut(BaseModel):
    source_type: str
    source_id: int
    title: str
    date: Optional[str] = None


class SiteReportIntelligenceOut(BaseModel):
    report_id: int
    project_id: int
    project_code: str
    project_name: str
    engineer: Optional[ReportEngineerOut] = None
    supervisor: Optional[ReportEngineerOut] = None
    report_date: str
    weather: str
    temperature: Optional[str] = None
    manpower: ReportManpowerOut
    equipment: list[str]
    completed_work: list[str]
    work_in_progress: list[str]
    materials_used: list[str]
    site_issues: list[str]
    delays: list[str]
    blockers: list[str]
    recommendations: list[str]
    safety_observations: list[str]
    quality_observations: list[str]
    photos: list[ReportAttachmentOut]
    attachments: list[ReportAttachmentOut]
    document_references: list[ReportDocumentReferenceOut]
    raw_summary: str


class AnalysisSourceOut(BaseModel):
    source_type: str
    source_id: str
    label: str
    excerpt: str


class AnalysisSectionSourceOut(BaseModel):
    section: str
    sources: list[str]


class SiteReportAnalysisOut(BaseModel):
    analysis_generated_from: str
    executive_summary: str
    progress_assessment: str
    delay_analysis: str
    risk_analysis: str
    safety_findings: list[str]
    quality_findings: list[str]
    schedule_impact: str
    recommended_actions: list[str]
    priority_level: str
    escalation_required: bool
    confidence_score: int
    section_sources: list[AnalysisSectionSourceOut]
    source_attribution: list[AnalysisSourceOut]
