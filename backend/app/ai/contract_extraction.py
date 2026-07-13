"""Contract Intelligence Extractor — Phase 2 of AMAD Document Intelligence.

Turns the OCR text already stored by Phase 1 (app/ai/document_ocr.py,
DocumentOCRResult) into a validated, structured JSON extraction of
construction-contract fields, via the configured LLM provider (Hermes).

Strict boundaries for this phase:
  - Never re-runs OCR. Input is always DocumentOCRResult.extracted_text.
  - The extraction is stored in its own table (ContractExtraction),
    separate from the OCR text — never duplicated back into
    document_ocr_results, never overwrites it.
  - No Copilot memory read/write (app/ai/memory.py is not imported here).
  - Not wired into app/ai/pipeline.py / the Copilot API in any way.
  - Only the fields explicitly supported by ContractFields are ever stored;
    anything else the model returns is dropped, never invented.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status as http_status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.ai.document_access import get_authorized_document
from app.ai.document_ocr import get_document_ocr_result
from app.ai.providers.base import LLMRequest, ProviderUnavailableError
from app.ai.providers.factory import get_llm_provider
from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.contract_extraction import ContractExtraction

logger = logging.getLogger(__name__)


class ContractFields(BaseModel):
    """The only fields this extractor is allowed to produce. Any other key
    the model returns is silently dropped (extra="ignore") — this phase
    extracts *only* these supported fields, never invents new ones."""

    contract_title: Optional[str] = None
    project_code: Optional[str] = None
    employer: Optional[str] = None
    contractor: Optional[str] = None
    contract_value: Optional[str] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    payment_terms: Optional[str] = None
    retention: Optional[str] = None
    liquidated_damages: Optional[str] = None
    insurance: Optional[str] = None
    key_obligations: Optional[list[str]] = None
    risks: Optional[list[str]] = None

    model_config = {"extra": "ignore"}


_FIELD_DESCRIPTIONS = """\
- contract_title: the contract's formal title/name
- project_code: the project code referenced in the contract (e.g. PRJ-0023)
- employer: the employer/client party name
- contractor: the contractor party name
- contract_value: the total contract value as written (keep currency out of this field)
- currency: the currency of the contract value (e.g. SAR, USD)
- start_date: the contract start date as written in the document
- completion_date: the contract completion/end date as written in the document
- payment_terms: a concise summary of payment terms
- retention: the retention percentage/terms as written
- liquidated_damages: the liquidated damages clause as written
- insurance: a concise summary of insurance requirements
- key_obligations: a list of short strings, each one key obligation
- risks: a list of short strings, each one identified risk or risk clause"""

_SYSTEM_PROMPT = f"""\
You are a construction-contract data extraction assistant. You will be \
given the raw text of one contract document (already extracted via OCR).

RULES (MANDATORY):
1. Extract ONLY the fields listed below. Do not add any other fields.
2. Use ONLY information present in the document text below. Never invent, \
guess, or infer a value that is not explicitly stated.
3. If a field is not present in the text, set it to null.
4. Output ONLY a single valid JSON object. No markdown code fences, no \
commentary, no explanation before or after the JSON.
5. key_obligations and risks must be JSON arrays of short strings (or null \
if none are stated).

SUPPORTED FIELDS:
{_FIELD_DESCRIPTIONS}

Respond with exactly one JSON object with these keys (and no others):
contract_title, project_code, employer, contractor, contract_value, \
currency, start_date, completion_date, payment_terms, retention, \
liquidated_damages, insurance, key_obligations, risks
"""

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

_RETRY_INSTRUCTION = (
    "Return exactly one valid JSON object. No markdown, no explanation, "
    "no trailing text."
)

# ── Deterministic fallback extractor ────────────────────────────────────
# Used only when both the original and retried Hermes calls fail to return
# valid, schema-conforming JSON. Extracts a field ONLY when its label
# appears explicitly as "Label: value" on its own line in the OCR text —
# never guesses, never infers. key_obligations/risks are intentionally not
# attempted: there's no safe deterministic way to split a labeled list
# without risking an incorrect split, so they stay null rather than guessed.
_FALLBACK_LABEL_PATTERNS: dict[str, re.Pattern] = {
    "contract_title": re.compile(r"(?im)^[ \t]*contract\s+title\s*:\s*(.+?)[ \t]*$"),
    "project_code": re.compile(r"(?im)^[ \t]*project\s*(?:code|reference)\s*:\s*(.+?)[ \t]*$"),
    "employer": re.compile(r"(?im)^[ \t]*employer\s*:\s*(.+?)[ \t]*$"),
    "contractor": re.compile(r"(?im)^[ \t]*contractor\s*:\s*(.+?)[ \t]*$"),
    "contract_value": re.compile(r"(?im)^[ \t]*contract\s+value\s*:\s*(.+?)[ \t]*$"),
    "currency": re.compile(r"(?im)^[ \t]*currency\s*:\s*(.+?)[ \t]*$"),
    "start_date": re.compile(r"(?im)^[ \t]*(?:start|commencement)\s+date\s*:\s*(.+?)[ \t]*$"),
    "completion_date": re.compile(r"(?im)^[ \t]*completion\s+date\s*:\s*(.+?)[ \t]*$"),
    "payment_terms": re.compile(r"(?im)^[ \t]*payment\s+terms?\s*:\s*(.+?)[ \t]*$"),
    "retention": re.compile(r"(?im)^[ \t]*retention\s*:\s*(.+?)[ \t]*$"),
    "liquidated_damages": re.compile(r"(?im)^[ \t]*liquidated\s+damages\s*:\s*(.+?)[ \t]*$"),
    "insurance": re.compile(r"(?im)^[ \t]*insurance\s*:\s*(.+?)[ \t]*$"),
}
_FALLBACK_CURRENCY_PREFIX_RE = re.compile(r"^([A-Z]{3})\s+(.+)$")


def _extract_labeled_fields_from_text(text: str) -> dict:
    """Scan the OCR text (never the LLM response) for explicitly labeled
    fields. Returns only the fields actually found — an empty dict means
    the fallback found nothing to extract."""
    found: dict[str, str] = {}
    for field, pattern in _FALLBACK_LABEL_PATTERNS.items():
        m = pattern.search(text)
        if m:
            value = m.group(1).strip().rstrip(".").strip()
            if value:
                found[field] = value

    # "Contract Value: SAR 12,500,000" -> split a leading 3-letter currency
    # code out of contract_value ONLY if no separate Currency: label was
    # found — still nothing invented, just structurally splitting text that
    # is already literally present.
    if "contract_value" in found and "currency" not in found:
        m = _FALLBACK_CURRENCY_PREFIX_RE.match(found["contract_value"])
        if m:
            found["currency"] = m.group(1)
            found["contract_value"] = m.group(2)

    return found


@dataclass
class ExtractionAttemptResult:
    status: str  # completed | failed
    provider: Optional[str] = None
    model_name: Optional[str] = None
    raw_response: Optional[str] = None
    extracted_fields: Optional[dict] = None
    validation_status: Optional[str] = None  # valid | invalid | fallback_valid
    validation_errors: Optional[str] = None
    error_message: Optional[str] = None


def _extract_balanced_json_object(text: str) -> Optional[str]:
    """Scan for the first balanced {...} object, respecting string
    literals (so a brace inside a quoted string can't confuse nesting
    depth). Returns None if no balanced object is found — deliberately
    more precise than a naive first-{-to-last-} span, which can incorrectly
    swallow trailing prose or a second object."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None  # never balanced — let json.loads report the real error


def _extract_json_text(raw: str) -> str:
    """Best-effort isolation of a JSON object from raw model output that may
    include markdown code fences and/or surrounding prose: strip fences
    first, then extract the first balanced {...} object."""
    text = raw.strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    balanced = _extract_balanced_json_object(text)
    return balanced if balanced is not None else text


def _validate_llm_output(raw_content: str) -> ExtractionAttemptResult:
    candidate = _extract_json_text(raw_content)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        return ExtractionAttemptResult(
            status="failed",
            raw_response=raw_content,
            validation_status="invalid",
            validation_errors=f"Response was not valid JSON: {e}",
            error_message="Extraction failed: model did not return valid JSON.",
        )

    if not isinstance(parsed, dict):
        return ExtractionAttemptResult(
            status="failed",
            raw_response=raw_content,
            validation_status="invalid",
            validation_errors="Top-level JSON value was not an object.",
            error_message="Extraction failed: model did not return a JSON object.",
        )

    try:
        fields = ContractFields.model_validate(parsed)
    except ValidationError as e:
        return ExtractionAttemptResult(
            status="failed",
            raw_response=raw_content,
            validation_status="invalid",
            validation_errors=str(e),
            error_message="Extraction failed: JSON did not match the expected contract schema.",
        )

    return ExtractionAttemptResult(
        status="completed",
        raw_response=raw_content,
        extracted_fields=fields.model_dump(),
        validation_status="valid",
    )


def _call_provider(provider, system_prompt: str, user_prompt: str):
    """Isolated call point — returns (response, error) so the caller can
    tell "got a response" apart from "provider raised". Never logs the
    prompt/OCR text itself."""
    try:
        return provider.generate(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.0)
        ), None
    except ProviderUnavailableError as e:
        return None, e


def extract_contract_fields(ocr_text: str) -> ExtractionAttemptResult:
    """Pure LLM-call + validation step — no DB, no auth. Input is OCR text
    (never re-extracted here). Never raises for LLM/validation failures;
    those become a status="failed" ExtractionAttemptResult.

    Order of attempts (each outcome logged as metadata only — never the OCR
    text or the full raw response):
      1. Hermes/provider, original prompt.
      2. If (1) returned a response but it failed JSON/schema validation:
         exactly one retry, with _RETRY_INSTRUCTION appended to the prompt.
      3. If both LLM attempts fail (or the provider was unreachable): a
         deterministic, conservative fallback over explicitly labeled
         "Label: value" lines in the OCR text (see
         _extract_labeled_fields_from_text) — never guesses. Success here
         is status="completed", validation_status="fallback_valid".
      Only when both Hermes and the fallback produce nothing usable is the
      result status="failed".
    """
    truncated_input = ocr_text[: settings.CONTRACT_EXTRACTION_MAX_INPUT_CHARS]
    provider = get_llm_provider()

    retry_used = False
    fallback_used = False
    last_response = None

    response, error = _call_provider(provider, _SYSTEM_PROMPT, truncated_input)
    if response is not None:
        last_response = response
        outcome = _validate_llm_output(response.content)

        if outcome.status == "failed":
            retry_used = True
            retry_response, _retry_error = _call_provider(
                provider, _SYSTEM_PROMPT + "\n\n" + _RETRY_INSTRUCTION, truncated_input,
            )
            if retry_response is not None:
                last_response = retry_response
                outcome = _validate_llm_output(retry_response.content)
    else:
        outcome = ExtractionAttemptResult(
            status="failed",
            error_message=f"LLM provider unavailable: {str(error)[:300]}",
        )

    if outcome.status == "failed":
        fallback_used = True
        fallback_fields = _extract_labeled_fields_from_text(ocr_text)
        if fallback_fields:
            validated = ContractFields.model_validate(fallback_fields)
            outcome = ExtractionAttemptResult(
                status="completed",
                raw_response=outcome.raw_response,
                extracted_fields=validated.model_dump(),
                validation_status="fallback_valid",
            )
        elif not outcome.error_message:
            outcome.error_message = (
                "Extraction failed: model did not return valid JSON, and no "
                "explicitly labeled fields were found in the document text."
            )

    # Provider/model metadata always reflects that Hermes was attempted,
    # even when the fallback ultimately produced the result.
    outcome.provider = last_response.provider if last_response else provider.provider_name
    outcome.model_name = last_response.model if last_response else provider.model_name
    if outcome.raw_response:
        outcome.raw_response = outcome.raw_response[
            : settings.CONTRACT_EXTRACTION_MAX_RAW_RESPONSE_CHARS
        ]

    logger.info(
        "contract_extraction_attempt hermes_attempted=true retry_used=%s "
        "fallback_used=%s final_status=%s validation_status=%s",
        retry_used, fallback_used, outcome.status, outcome.validation_status,
    )
    return outcome


def process_contract_extraction(
    db: Session,
    scope: AIAuthScope,
    document_id: int,
) -> ContractExtraction:
    """Authorize, load the existing OCR text (never re-running OCR), call
    the LLM provider, validate its JSON output, and persist one auditable
    ContractExtraction row per document (upserted on reprocess)."""
    document = get_authorized_document(db, scope, document_id)

    ocr_result = get_document_ocr_result(db, scope, document_id)
    if ocr_result.status != "completed" or not ocr_result.extracted_text:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="OCR text is not available for this document yet (run OCR first).",
        )

    row = (
        db.query(ContractExtraction)
        .filter(ContractExtraction.document_id == document_id)
        .first()
    )
    if row is None:
        row = ContractExtraction(document_id=document_id, project_id=document.project_id)
        db.add(row)

    row.status = "processing"
    row.ocr_result_id = ocr_result.id
    row.organization_id = document.organization_id
    row.project_id = document.project_id
    row.requested_by = scope.user_id
    row.error_message = None
    db.flush()

    try:
        outcome = extract_contract_fields(ocr_result.extracted_text)
    except Exception:
        logger.exception("contract_extraction_error document_id=%s", document_id)
        outcome = ExtractionAttemptResult(
            status="failed", error_message="Extraction failed unexpectedly.",
        )

    row.status = outcome.status
    row.provider = outcome.provider
    row.model_name = outcome.model_name
    row.raw_response = outcome.raw_response
    row.extracted_fields = outcome.extracted_fields
    row.validation_status = outcome.validation_status
    row.validation_errors = outcome.validation_errors
    row.error_message = outcome.error_message
    db.commit()
    db.refresh(row)

    logger.info(
        "contract_extraction_processed document_id=%s status=%s "
        "validation_status=%s provider=%s",
        document_id, row.status, row.validation_status, row.provider,
    )
    return row


def get_contract_extraction(
    db: Session, scope: AIAuthScope, document_id: int
) -> ContractExtraction:
    get_authorized_document(db, scope, document_id)

    row = (
        db.query(ContractExtraction)
        .filter(ContractExtraction.document_id == document_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No contract extraction exists for this document yet.",
        )
    return row
