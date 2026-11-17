"""Build the one user-facing result from the available report evidence."""

from .fraud_risk import score_alert, update_fraud_risk
from .image_risk import assess_image
from .image_marks import SUPPORTED_MARK_POLICIES
from .risk_labels import INCOMPLETE, NO_CLEAR_RISK, REVIEW


def _refresh_text_assessments(report):
    from .chat_assessment import ASSESSMENT_VERSION, enrich

    for raw, analysis in (("ocr", "chat_analysis"), ("transcript", "speech_analysis")):
        text = (report.get(raw) or {}).get("text")
        content = report.get(analysis) or {}
        version = (content.get("assessment") or {}).get("version")
        if text and version and version != ASSESSMENT_VERSION:
            content["signals"], content["assessment"] = enrich(text, content.get("signals", []))


def update_summary(report):
    _refresh_text_assessments(report)
    modules = report.get("modules", {})
    if "image" in modules or "tamper" in modules:
        mark_policy = report.get("mark_policy")
        if mark_policy not in SUPPORTED_MARK_POLICIES:
            report.pop("marked_jpeg", None)
        report["image_risk"] = assess_image(modules, mark_policy=mark_policy if report.get("marked_jpeg") else None)
        report["summary"] = report["image_risk"]["title"]
    else:
        content = report.get("chat_analysis") or report.get("speech_analysis")
        level = (content or {}).get("assessment", {}).get("level")
        checked = [item.get("status") for item in modules.values() if item.get("status") != "disabled"]
        if content is not None:
            checked.append(content.get("status"))
        if level in {"attention", "alert"} or any(score_alert(item) for item in modules.values()):
            report["summary"] = REVIEW
        else:
            report["summary"] = NO_CLEAR_RISK if checked and all(status == "completed" for status in checked) else INCOMPLETE
    update_fraud_risk(report)
    return report
