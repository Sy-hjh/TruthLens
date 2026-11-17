"""Image evidence weights used for report decisions."""

from .fraud_risk import score_alert
from .image_marks import (
    DAF_YELLOW_POLICIES, FUSED_YELLOW_POLICIES, MARK_POLICY, SUPPORTED_MARK_POLICIES,
    combined_regions, daf_review_regions, report_regions,
)
from .risk_labels import INCOMPLETE, NO_CLEAR_RISK, PRIORITY_REVIEW, REVIEW

GUIDANCE = {
    "competition": ("图中有赛事获奖信息。", "从主办方的官方查询入口核对证书编号，再比对奖项、项目名称和团队成员。"),
    "certificate": ("图中有证书信息。", "通过发证机构的官方入口，用证书编号核对证书内容。"),
    "transaction": ("图中有交易凭证信息。", "打开原订单或支付记录，逐项核对编号和金额。"),
    "contract": ("图中有合同信息。", "找到签署平台的原始版本，核对双方、金额及签署日期。"),
    "medical": ("图中有医疗报告信息。", "在出具机构的系统里核对报告编号和原始记录。"),
    "education": ("图中有教学材料信息。", "在原提交平台核对提交记录、作者和相关字段。"),
    "image": ("", "找到图片的原始文件或最早的发布记录，核对关键内容。"),
}


def assess_image(modules, *, mark_policy=None):
    whole, local, daf, reference = (modules.get(key, {}) for key in ("image", "tamper", "daf", "reference"))
    whole_checked = whole.get("status") == "completed"
    local_checked = local.get("status") == "completed"
    whole_signal = score_alert(whole)
    generation_label = whole.get("generation_label")
    diffuse_mask = local_checked and local.get("relevance") == "diffuse"
    regions = local.get("regions", []) if local_checked else []
    text_regions = daf.get("regions", []) if daf.get("status") == "completed" else []
    differences = reference.get("regions", []) if reference.get("status") == "completed" else []
    fields = local.get("document_fields", [])
    agreed = list(dict.fromkeys(region["field"] for region in combined_regions(modules)))
    daf_reviews = daf_review_regions(modules)
    text_fields = {region["field"] for region in text_regions}
    diffuse_text = len(text_fields) >= 3 and len(text_fields) >= 0.6 * len(fields)
    text_signal = bool(agreed or daf_reviews) or (bool(text_regions) and whole_signal and not diffuse_text)
    whole_note = ("达到提醒线" if whole_signal else "低于提醒线") if whole_checked else "检查未完成"
    score = whole.get("score")
    if whole_checked and isinstance(score, (int, float)):
        whole_note = f"模型分 {score:.2f}，{whole_note} {whole.get('threshold', 0.5):.2f}"
    local_note = {
        "no_response": "未发现明显重绘线索",
        "irrelevant": "异常未落在任务关键信息上，未计入",
        "unmatched": "异常未能关联到可定位的任务信息，未计入",
        "unavailable": "未能完成任务信息定位，未计入",
        "diffuse": "热图响应覆盖几乎全图，未能定位",
    }.get(local.get("relevance"), "检查未完成")
    labels = list(dict.fromkeys(region["field"] for region in regions if region.get("field")))
    if regions:
        local_note = "异常涉及" + "、".join(labels) if labels else "发现需要复核的重绘线索"
    description, next_step = GUIDANCE.get(local.get("document_kind"), GUIDANCE["image"])
    if description and fields:
        preferred = ("获奖等级", "团队成员", "证书编号", "项目名称", "赛项名称")
        ordered = [field for field in preferred if field in fields]
        visible = list(dict.fromkeys(ordered + fields))[:3]
        description = description.rstrip("。") + "，识别到" + "、".join(visible) + "。"
    findings = [description] if description else []
    if whole_signal:
        findings.append("整张图片出现合成线索。")
    if generation_label:
        findings.append(f"图中可见「{generation_label}」标记。")
        if not (regions or text_signal or differences):
            findings.append("当前未定位到具体改动字段。")
    if differences:
        locations = "、".join(dict.fromkeys(region["field"] for region in differences))
        findings.append(f"与选定参考图相比，「{locations}」有差异。")
        next_step = "确认参考图的来源，再用原始记录核对这些字段。"
    if agreed:
        suffix = "，红框标出重合区域。" if mark_policy in SUPPORTED_MARK_POLICIES else "。"
        findings.append("FUSED 与 DAF 均在「" + "、".join(agreed) + "」发现线索" + suffix)
    elif regions:
        locations = "、".join(labels)
        findings.append(f"FUSED 在「{locations}」附近发现可复核的重绘线索。" if locations else "FUSED 发现可复核的局部重绘线索。")
    elif diffuse_mask:
        findings.append("重绘模型的响应覆盖几乎整张图，无法定位可疑部位，现有线索不足以确认是否改动。")
    markers = report_regions(modules) if mark_policy in FUSED_YELLOW_POLICIES else []
    if any(region["detectors"] == ["tamper"] for region in markers):
        findings.append("黄框为 FUSED 线索，建议复核。")
    if text_signal and not agreed:
        locations = "、".join(dict.fromkeys(region["field"] for region in daf_reviews or text_regions))
        findings.append(f"DAF 在「{locations}」附近发现疑似局部文字编辑线索。")
    if mark_policy in DAF_YELLOW_POLICIES and any(region["detectors"] == ["daf"] for region in markers):
        locations = "、".join(dict.fromkeys(region["field"] for region in markers if region["detectors"] == ["daf"]))
        findings.append(f"黄框标出「{locations}」的 DAF 线索，建议复核。")
    if mark_policy == MARK_POLICY and any(region["detectors"] == ["reference"] for region in markers):
        findings.append("蓝框标出与参考图的差异位置。")
    if reference.get("status") == "unavailable" and reference.get("note"):
        findings.append(reference["note"])
    if not findings:
        findings.append("可根据材料来源和原始记录核对关键信息。")
    evidence = [
        {"label": "整图 AI 生成", "weight": whole.get("weight",30), "triggered": whole_signal, "note": whole_note},
        {"label": "FUSED 重绘", "weight": local.get("weight",45), "triggered": bool(regions), "note": local_note},
    ]
    if daf and daf.get("status") != "disabled":
        evidence.append({"label": "DAF 文字编辑", "weight": daf.get("weight",25), "triggered": text_signal,
         "note": "任务相关字段达到提醒条件" if text_signal else
                 "多处字段响应，缺少其他检测线索支持" if diffuse_text else
                 "有单项文字编辑响应，缺少其他检测线索支持" if text_regions else
                 "检查未完成" if daf.get("status") == "unavailable" else "暂无触发线索"})
    total = sum(item["weight"] for item in evidence if item["triggered"])
    title = (PRIORITY_REVIEW if agreed or (whole_signal and (regions or text_signal or differences)) else REVIEW if total or differences or diffuse_mask or generation_label else
             NO_CLEAR_RISK if whole_checked and local_checked and daf.get("status") != "unavailable" else INCOMPLETE)
    return {"title": title, "points": total, "findings": findings, "next_step": next_step, "evidence": evidence}
