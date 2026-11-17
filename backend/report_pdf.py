"""PDF export of stored inspection evidence."""

import base64
import math
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from .agent_review import report_facts
from .image_marks import SUPPORTED_MARK_POLICIES
from .image_risk import assess_image
from .risk_labels import PRIORITY_REVIEW, REVIEW

INK = HexColor("#251c2d")
ACCENT = HexColor("#573869")
MUTED = HexColor("#625969")
RULE = HexColor("#ddd6e2")
MODULES = {"image": "整图生成", "tamper": "局部篡改", "video": "视频画面", "audio": "声音"}


@lru_cache(maxsize=1)
def report_font():
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("msyh.ttc", "simhei.ttf"):
        candidate = fonts / filename
        if candidate.is_file():
            try:
                pdfmetrics.registerFont(TTFont("TruthLensCN", str(candidate)))
                return "TruthLensCN"
            except (OSError, TTFError):
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def build_report_pdf(report):
    font = report_font()
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, topMargin=55, bottomMargin=57,
                                 leftMargin=52, rightMargin=52, title="真鉴核验报告", author="TruthLens 真鉴")
    styles = {
        "title": ParagraphStyle("Title", fontName=font, textColor=INK, fontSize=27, leading=36, spaceAfter=15),
        "head": ParagraphStyle("Heading", fontName=font, textColor=ACCENT, fontSize=16, leading=23, spaceBefore=13, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("Body", fontName=font, textColor=INK, fontSize=10.5, leading=17, spaceAfter=6, wordWrap="CJK"),
        "small": ParagraphStyle("Small", fontName=font, textColor=MUTED, fontSize=9, leading=15, spaceAfter=4, wordWrap="CJK"),
    }
    story = []

    def add(text, style="body"):
        clean = "".join(c for c in str(text) if c in "\n\t" or ord(c) >= 32)
        story.append(Paragraph(escape(clean).replace("\n", "<br/>"), styles[style]))

    fraud = report.get("fraud_risk")
    modules = report.get("modules", {})
    if "image" in modules or "tamper" in modules:
        styles["body"].fontSize = 12
        styles["body"].leading = 19
        styles["small"].fontSize = 10
        image_risk = report.get("image_risk", {})
        if "next_step" not in image_risk:
            image_risk = assess_image(modules)
        title = report["summary"] if fraud else image_risk["title"]
        if title in {REVIEW, PRIORITY_REVIEW}:
            styles["title"].textColor = HexColor("#a51731")
        add(title, "title")
        add(report.get("filename") or "未命名", "small")
        add("内容分析", "head")
        if not fraud or not fraud.get("language_reason") or fraud["synthesis"] == "发现线索" or report.get("marked_jpeg"):
            add("".join(image_risk["findings"]))
        if fraud:
            if fraud.get("language_reason"):
                add(fraud["language_reason"])
            add(f"合成线索  {fraud['synthesis']}")
            add(f"诈骗话术  {fraud['language']}")
        add("下一步", "head")
        add((fraud or {}).get("next_step") or image_risk["next_step"])
        show_marks = title in {REVIEW, PRIORITY_REVIEW}
        marked = report.get("marked_jpeg") if show_marks and report.get("mark_policy") in SUPPORTED_MARK_POLICIES else None
        if marked:
            photo = Image(BytesIO(base64.b64decode(marked)))
            available_width = document.width - 12
            content_height = sum(
                item.wrap(available_width, document.height)[1] + item.getSpaceBefore() + item.getSpaceAfter()
                for item in story
            )
            max_height = max(120, document.height - content_height - 26)
            scale = min(available_width / photo.imageWidth, max_height / photo.imageHeight)
            photo.drawWidth = photo.imageWidth * scale
            photo.drawHeight = photo.imageHeight * scale
            photo.hAlign = "CENTER"
            story.extend((Spacer(1, 10), photo))
        document.build(story)
        return stream.getvalue()

    add("真鉴核验报告", "title")
    add(f"材料  {report.get('filename') or '未命名'}", "small")
    add(f"记录编号  {report.get('id', '')}    ·    检测时间  {report.get('created_at', '')}", "small")
    story.append(Spacer(1, 5))
    add("发现了什么", "head")
    add(report.get("summary") or "请查看本次的分项核验结果。")
    if fraud:
        add(f"合成线索  {fraud['synthesis']}")
        add(f"诈骗话术  {fraud['language']}")
    facts, _ = report_facts(report, "")
    for fact in facts:
        add(fact)

    add("依据是什么", "head")
    found_evidence = False
    for key, label in MODULES.items():
        result = (report.get("modules") or {}).get(key) or {}
        if not result or result.get("status") == "disabled":
            continue
        found_evidence = True
        status = "已完成" if result.get("status") == "completed" else "未取得有效检测结果"
        score, threshold = result.get("score"), result.get("threshold")
        details = [label, status]
        if result.get("status") == "completed":
            for name, value in (("检测分数", score), ("触发阈值", threshold)):
                if isinstance(value, (int, float)) and math.isfinite(value):
                    details.append(f"{name} {value:.4f}")
        add(" · ".join(details))
        if result.get("note"):
            add(result["note"], "small")
        for segment in (result.get("segments") or [])[:12]:
            start, end, value = segment.get("start"), segment.get("end"), segment.get("score")
            time = f"{start:g} 秒" if isinstance(start, (int, float)) else "片段"
            if isinstance(end, (int, float)):
                time += f"至 {end:g} 秒"
            if isinstance(value, (int, float)) and math.isfinite(value):
                add(f"{time} · 模型分数 {value:.4f}", "small")

    for field, label in (("ocr", "截图原话"), ("transcript", "语音转写")):
        value = (report.get(field) or {}).get("text")
        if value:
            found_evidence = True
            excerpt = value[:1200] + ("（节选）" if len(value) > 1200 else "")
            add(f"{label}  {excerpt}", "small")
    if not found_evidence:
        add("本次没有可列出的检测分项或原话。", "small")

    add("下一步怎么核实", "head")
    if fraud and fraud.get("next_step"):
        add(fraud["next_step"])
    elif report.get("scene") == "chat":
        add("回到原会话核对原话和上下文，再通过原订单、原业务系统或可信渠道确认消息来源。")
    else:
        add("找到原始材料和最早的提交或发布记录，对照上面的线索和片段，再通过可信来源核实。")
    add("检测结果用于辅助核实。请结合原始材料、来源和实际情况作判断。", "small")

    def footer(canvas, page):
        canvas.setStrokeColor(RULE)
        canvas.line(52, 42, A4[0] - 52, 42)
        canvas.setFillColor(MUTED)
        canvas.setFont(font, 8)
        canvas.drawString(52, 28, "TruthLens 真鉴  /  核验记录")
        canvas.drawRightString(A4[0] - 52, 28, f"第 {page.page} 页")

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
