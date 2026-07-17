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


class RecommendedActionOut(BaseModel):
    action: str
    priority: str
    reason: str
    evidence_refs: list[str]
    expected_benefit: str


class PriorityMatrixItemOut(BaseModel):
    item: str
    urgency: str
    impact: str
    evidence_refs: list[str]


class TrendAnalysisOut(BaseModel):
    available: bool
    summary: Optional[str] = None
    signals: list[str] = []


class RiskScoreComponentOut(BaseModel):
    key: str
    label: str
    occurrences: int
    points: int
    max_points: int
    rationale: str
    evidence_refs: list[str]


class RiskScoreBreakdownOut(BaseModel):
    total: int
    level: str
    components: list[RiskScoreComponentOut]


class SiteReportAnalysisOut(BaseModel):
    analysis_generated_from: str

    # Reasoning-pipeline status — always present so the frontend can show an
    # honest "AI reasoning unavailable" state instead of silently rendering
    # empty/stale sections when Hermes couldn't be reached or its output
    # failed validation. "completed" means every section below was produced
    # by the Hermes reasoning pass; "unavailable" means it was not, and the
    # narrative fields will be empty/None (the deterministic evidence/report
    # payload from the /intelligence endpoint and risk_score_breakdown below
    # are unaffected either way).
    reasoning_status: str
    reasoning_provider: Optional[str] = None
    reasoning_model: Optional[str] = None
    reasoning_error: Optional[str] = None

    insufficient_evidence: bool = False
    insufficient_evidence_reason: Optional[str] = None
    ocr_quality_note: Optional[str] = None

    executive_summary: str
    major_findings: list[str] = []
    safety_findings: list[str] = []
    quality_findings: list[str] = []
    schedule_findings: list[str] = []
    procurement_findings: list[str] = []
    equipment_issues: list[str] = []
    weather_impact: str = ""
    blocked_activities: list[str] = []
    critical_risks: list[str] = []
    recommended_actions: list[RecommendedActionOut] = []
    priority_matrix: list[PriorityMatrixItemOut] = []
    next_site_visit_focus: list[str] = []
    questions_for_site_team: list[str] = []
    contradictions: list[str] = []
    trend_analysis: TrendAnalysisOut
    # New, additive field from the compact Hermes output contract (AMAD AI
    # Stabilization) — what the model flagged as missing rather than what
    # it found. Also mirrored into questions_for_site_team for existing
    # frontend consumers that already render that field.
    missing_information: list[str] = []

    # Mathematically-derived risk index (0-100), NOT a fabricated
    # LLM-confidence percentage — see app/ai/site_report_risk_scoring.py for
    # the transparent, auditable formula. Field name kept as
    # `confidence_score` for wire compatibility with existing consumers;
    # its value is now risk_score_breakdown.total. Prefer
    # risk_score_breakdown for anything that needs the reasoning behind it.
    confidence_score: int
    risk_score_breakdown: RiskScoreBreakdownOut

    priority_level: str
    escalation_required: bool

    # Deprecated — superseded by major_findings / schedule_findings /
    # critical_risks, which are evidence-cited and report-scoped instead of
    # generic prose. Left as optional/empty for any existing consumer that
    # still reads them; no longer populated with meaningful content.
    progress_assessment: str = ""
    delay_analysis: str = ""
    risk_analysis: str = ""
    schedule_impact: str = ""

    section_sources: list[AnalysisSectionSourceOut]
    source_attribution: list[AnalysisSourceOut]
