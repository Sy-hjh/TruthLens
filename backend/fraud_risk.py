"""Combine independent findings for suspected fraud materials."""

import re

from .risk_labels import INCOMPLETE, NO_CLEAR_RISK, PRIORITY_REVIEW, REVIEW


_EDUCATION = re.compile(r"反诈(?:课堂|教育|宣传|提醒)|防骗(?:教程|提醒)|诈骗案例(?:讲解|分析)|课堂演示")
_FRAUD_CONTEXT = re.compile(r"诈骗|可疑退款|钓鱼|骗子|冒充|骗我|骗取|骗赔|骗补偿|疑似被骗")
_REQUEST_CONTEXT = re.compile(r"转账|转.{0,4}钱|付款|汇款|借(?:钱|款|我|点|[0-9０-９])|验证码|密码|银行卡号|屏幕共享|远程操作")
_VERIFY_CONTEXT = re.compile(r"真假|是不是真的|是否真实|真不真|核实|核验|真的吗|不对劲|可疑|被骗")
_SENSITIVE = re.compile(r"验证码|密码|口令|六位数字|银行卡号|卡号")
_REMOTE_CONTROL = re.compile(r"远程控制|远控|接管|共享屏幕.{0,18}(?:银行|验证码|密码|付款)")
_REQUESTS = {"money", "credentials", "remote", "link", "investment", "secrecy"}


def is_fraud_task(context):
    return not _EDUCATION.search(context) and bool(
        _FRAUD_CONTEXT.search(context) or (_REQUEST_CONTEXT.search(context) and _VERIFY_CONTEXT.search(context))
    )


def has_fraud_language(analysis, *, task=False):
    level = (analysis.get("assessment") or {}).get("level")
    if level not in {"attention", "alert"}:
        return False
    signals = analysis.get("signals", [])
    categories = {signal["category"] for signal in signals}
    if not categories & _REQUESTS:
        return False
    if task or level == "alert":
        return True
    if any((signal["category"] == "credentials" and _SENSITIVE.search(signal["quote"])) or
           (signal["category"] == "remote" and _REMOTE_CONTROL.search(signal["quote"])) for signal in signals):
        return True
    return bool(categories & {"money", "credentials", "link", "investment", "remote"} and
                categories & {"pressure", "secrecy"})


def score_alert(module):
    if module.get("status") != "completed":
        return False
    for value in (module, *module.get("segments", [])):
        score = value.get("score")
        if isinstance(score, (int, float)) and score >= value.get("threshold", 0.5):
            return True
    return False


def update_fraud_risk(report):
    """Recompute the warning from stored results, including after text corrections."""
    report.pop("fraud_risk", None)
    task = is_fraud_task(report.get("context", ""))
    content = report.get("chat_analysis") or report.get("speech_analysis") or {}
    language = has_fraud_language(content, task=task)
    if not (language or task):
        return

    modules = report.get("modules", {})
    scored = [modules[name] for name in ("image", "audio", "video") if name in modules]
    tamper = modules.get("tamper", {})
    fused = tamper.get("method") == "fused" and tamper.get("status") == "completed"
    image_evidence = report.get("image_risk", {}).get("evidence", [])
    image_signal = any(item.get("triggered") for item in image_evidence)
    synthesis = any(score_alert(module) for module in scored) or bool(fused and tamper.get("regions")) or image_signal
    media_checked = fused or any(module.get("status") == "completed" for module in scored)
    language_checked = content.get("extraction_status") != "unavailable" and content.get("status") == "completed"
    high = synthesis and language
    report["fraud_risk"] = {
        "level": "high" if high else "review",
        "synthesis": "发现线索" if synthesis else "未发现明显线索" if media_checked else "检查未完成",
        "language": "发现需核实的话术" if language else "未发现明确风险话术" if language_checked else "检查未完成",
    }
    if language and (content.get("assessment") or {}).get("summary"):
        first_sentence = content["assessment"]["summary"].split("。", 1)[0]
        report["fraud_risk"]["language_reason"] = first_sentence + "。"
    image_title = report.get("image_risk", {}).get("title")
    if high or image_title == PRIORITY_REVIEW:
        report["summary"] = PRIORITY_REVIEW
    elif synthesis or language or image_title == REVIEW:
        report["summary"] = REVIEW
    else:
        report["summary"] = NO_CLEAR_RISK if media_checked and language_checked else INCOMPLETE
    report["fraud_risk"]["next_step"] = "先暂停按对方要求操作，通过原有的可信渠道核对身份和请求。" if synthesis or language else "通过原会话、订单或机构的官方入口核对消息来源。"
