"""Match forensic responses against visible, task-relevant OCR fields."""

import re

import numpy as np


_LABEL = re.compile(
    r"^(?:赛项|比赛|竞赛|赛事|项目|产品|商品|药品|课程|单位|企业|公司|学校|机构|文件|报告|论文|合同)名称"
    r"|^(?:奖项|奖级|获奖等级|比赛成绩|分数|成绩|等级|姓名|持证人|选手姓名|团队成员|队伍成员|参赛成员|项目成员|成员姓名|参赛单位|学生姓名|患者姓名|签发人|收款人|付款人|签约方|委托方|甲方|乙方|作者|所在院校|签发单位|发证机关|主办单位|指导教师|指导老师|诊断|检验结果|检测结果|数量|剂量|规格|单价|总价|金额|合计|税额|应付金额|实付金额|退款金额|交易金额|银行卡号|银行账号)"
    r"|^(?:证书|商品|订单|运单|发票|合同|报告|文件|项目|许可证|证件|账户|交易|批次)(?:号码|编号|号)"
    r"|^(?:签发|有效|到期|交易|开票|检测|生产|签署|出具|交付)(?:日期|时间|期限)"
)
_STANDALONE = (
    (re.compile(r"^(?:特|[一二三四五六七八九]|[1-9])\s*等[奖獎]$|^(?:金|银|铜)奖$"), "获奖等级"),
    (re.compile(r"^(?:[￥¥$]\s*[\d,.]+|[\d,.]+\s*(?:元|万元|美元))$"), "金额"),
)
_ALIASES = {"获奖等级": ("几等奖", "几等", "奖级"), "赛项名称": ("赛项", "比赛名称", "竞赛项目"),
            "选手姓名": ("参赛人", "选手名字"), "退款金额": ("退多少钱", "退费金额"),
            "团队成员": ("成员", "参赛名单", "队员"), "队伍成员": ("成员", "参赛名单", "队员"),
            "参赛成员": ("成员", "参赛名单", "队员"), "项目成员": ("成员", "项目名单"),
            "成员姓名": ("成员", "名单")}
_GENERAL_TASK = re.compile(
    r"(?:请|帮我|麻烦|小鉴|想|要)*(?:核验|核实|检测|检查|看一下|看看|看下|分析|辨别)?"
    r"(?:这份|这张|这个)?(?:获奖证书|图片|图|证书|照片|材料|截图|发票|报告|合同|凭证|票据|作业)?(?:的)?"
    r"(?:真假|真伪|是否真实|真的假的|(?:是否|是不是|有没有|有无)(?:ai生成|合成|篡改|改动|造假|p过|p)的?)?(?:吗|呢)?"
)
_GENERATION_LABEL = re.compile(r"(?:[a-z\u4e00-\u9fff]{1,10})?(?:ai|人工智能)(?:生成|合成|制作|编辑)(?:内容|图片|图像)?|aigenerated|generatedbyai")
_LABEL_QUALIFIER = re.compile(r"非|不是|并非|未|疑似|可能|检测|鉴别|识别|确认|是否|请勿|禁止|防范|不确定")


def _compact(text):
    return re.sub(r"[^\w]+", "", text.lower())


def document_kind(lines):
    text = " ".join(row["text"] for row in lines if row.get("confidence", 0) >= 0.65)
    if re.search(r"大赛|竞赛|获奖|参赛|等[奖獎]", text) and re.search(r"证书|奖[级項项]|等[奖獎]|团队成员", text):
        return "competition"
    for pattern, kind in ((r"检验报告|检验结果|患者姓名|病历", "medical"),
                          (r"发票|订单编号|订单号|退款金额|交易金额", "transaction"),
                          (r"合同编号|合同名称|甲方.{0,100}乙方", "contract"),
                          (r"证书编号|发证机关|签发单位|许可证", "certificate"),
                          (r"论文名称|学生姓名|课程名称|成绩单", "education")):
        if re.search(pattern, text):
            return kind
    return "image"


def _row_fields(lines, context, *, explicit_only=False):
    task = _compact(context.removeprefix("__truthlens_qa__"))
    rows = []
    for line in lines:
        if line.get("confidence", 0) < 0.65:
            continue
        text = line["text"].strip()
        xs, ys = zip(*line["box"])
        rows.append((text, (min(xs), min(ys), max(xs), max(ys))))
    fields = {}
    competition = any(re.search(r"大赛|竞赛|赛事|参赛|获奖证书", text) for text, _ in rows)
    for index, (text, box) in enumerate(rows):
        leading, separator, value = text.partition("：" if "：" in text else ":")
        label = re.sub(r"\s+", "", leading)
        label_token = _compact(label)
        named_in_task = separator and 2 <= len(label_token) <= 16 and label_token in task
        match = _LABEL.fullmatch(label) or named_in_task
        if match and separator and value.strip():
            fields[index] = label
        elif match and not separator:
            _, y1, x2, y2 = box
            candidates = []
            for candidate, (other, (left, top, _, bottom)) in enumerate(rows):
                overlap = min(y2, bottom) - max(y1, top)
                if left >= x2 and overlap >= 0.55 * min(y2 - y1, bottom - top) and not _LABEL.fullmatch(other):
                    candidates.append((left, candidate))
            if candidates:
                fields[min(candidates)[1]] = label
        for pattern, name in _STANDALONE:
            if pattern.fullmatch(text):
                fields.setdefault(index, name)
        if competition and re.fullmatch(r"等\s*[奖獎]", text):
            fields.setdefault(index, "获奖等级")

    explicit = {index: label for index, label in fields.items()
                if any(_compact(name) in task for name in (label, *_ALIASES.get(label, ())))}
    for index, (text, _) in enumerate(rows):
        token = _compact(text)
        if len(token) >= 4 and token in task:
            explicit[index] = fields.get(index) or "指定内容"
    if explicit_only or explicit or (task and not _GENERAL_TASK.fullmatch(task)):
        fields = explicit
    return [(rows[index][1], label) for index, label in fields.items()]


def field_names(lines):
    return list(dict.fromkeys(label for _, label in _row_fields(lines, "")))


def task_fields(lines, size, context, *, explicit_only=False):
    width, height = size
    return [([left / width, top / height, right / width, bottom / height], label)
            for (left, top, right, bottom), label in _row_fields(lines, context, explicit_only=explicit_only)]


def visible_generation_label(lines, size):
    """Find a short, clearly readable AI disclosure in a corner of the image."""
    width, height = size
    for line in lines:
        text = line["text"].strip()
        token = _compact(text)
        if line.get("confidence", 0) < 0.9 or _LABEL_QUALIFIER.search(token) or not _GENERATION_LABEL.fullmatch(token):
            continue
        xs, ys = zip(*line["box"])
        in_corner = (min(xs) <= 0.1 * width or max(xs) >= 0.9 * width) and (min(ys) <= 0.1 * height or max(ys) >= 0.9 * height)
        if in_corner and max(xs) - min(xs) <= 0.35 * width and max(ys) - min(ys) <= 0.07 * height:
            return text
    return None


def relevant_regions(mask, lines, image_size, context="", *, threshold=0.50):
    """Require actual mask overlap with a field, rather than overlapping rectangles."""
    fields = _row_fields(lines, context)
    height, width = mask.shape
    scale_x, scale_y = width / image_size[0], height / image_size[1]
    result = []
    for (left, top, right, bottom), label in fields:
        x1, y1 = max(0, round(left * scale_x)), max(0, round(top * scale_y))
        x2, y2 = min(width, round(right * scale_x)), min(height, round(bottom * scale_y))
        crop = mask[y1:y2, x1:x2]
        if not crop.size:
            continue
        ys, xs = np.nonzero(crop >= round(255 * threshold))
        if len(xs) < max(16, 0.18 * crop.size):
            continue
        result.append({
            "box": [(x1 + int(xs.min())) / width, (y1 + int(ys.min())) / height,
                    (x1 + int(xs.max()) + 1) / width, (y1 + int(ys.max()) + 1) / height],
            "field": label, "peak": round(float(crop.max()) / 255, 4), "pixels": len(xs),
        })
    return sorted(result, key=lambda region: region["pixels"], reverse=True)[:5], bool(fields)
