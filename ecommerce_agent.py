"""Ecommerce Agent routes and persistent orchestration.

All state lives below data/ecommerce. Canvas files, API settings and history
are never rewritten by this module.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
import zipfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

import requests
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


PLATFORMS = {
    # 保留旧平台字段兼容历史任务；新画布 Agent 默认使用这个中性创作通道。
    "canvas": {"label": "画布创作", "size": "1024x1024", "focus": "适合在无限画布中继续创作与迭代"},
    "taobao": {"label": "淘宝/天猫", "size": "1080x1080", "focus": "搜索主图、核心卖点、参数与详情结构"},
    "douyin": {"label": "抖音电商", "size": "1080x1080", "focus": "强视觉首图、使用场景与短句卖点"},
    "pdd": {"label": "拼多多", "size": "1080x1080", "focus": "商品清晰、优惠信息与核心功能直达"},
    "xiaohongshu": {"label": "小红书", "size": "1242x1660", "focus": "生活方式、场景氛围与种草表达"},
    "detail": {"label": "详情页模块", "size": "750x1000", "focus": "模块化卖点、参数、场景与细节说明"},
}

# 通用详情页模板只描述创作结构，不绑定任何电商平台或上架流程。
DETAIL_TEMPLATES = [
    {
        "id": "basic-detail", "name": "基础详情页",
        "description": "从商品主图到核心卖点，适合大多数商品的完整介绍。",
        "recommended_count": 6,
        "modules": [
            {"id": "cover", "name": "首屏主图", "purpose": "先让用户看清商品和第一印象", "kind": "商品主图", "text_hint": "一句话核心卖点"},
            {"id": "selling-point", "name": "核心卖点", "purpose": "集中说明最重要的优势", "kind": "场景图", "text_hint": "卖点标题 + 简短说明"},
            {"id": "detail", "name": "细节展示", "purpose": "放大材质、结构或工艺细节", "kind": "细节图", "text_hint": "细节名称"},
            {"id": "use", "name": "使用场景", "purpose": "让用户直观看到商品怎么使用", "kind": "场景图", "text_hint": "适用场景"},
            {"id": "spec", "name": "信息说明", "purpose": "整理用户最关心的参数和注意事项", "kind": "信息图", "text_hint": "参数或使用说明"},
            {"id": "after-sale", "name": "收尾说明", "purpose": "补充品牌感和售后提示", "kind": "品牌图", "text_hint": "温馨提示"},
        ],
    },
    {
        "id": "selling-points", "name": "卖点介绍",
        "description": "突出 3 至 5 个核心优势，适合功能型商品。", "recommended_count": 5,
        "modules": [
            {"id": "cover", "name": "商品亮相", "purpose": "展示商品整体外观", "kind": "商品主图", "text_hint": "核心卖点"},
            {"id": "point-1", "name": "卖点一", "purpose": "讲清最有价值的功能", "kind": "功能图", "text_hint": "功能标题"},
            {"id": "point-2", "name": "卖点二", "purpose": "说明使用体验或材质", "kind": "功能图", "text_hint": "体验说明"},
            {"id": "point-3", "name": "卖点三", "purpose": "补充差异化优势", "kind": "功能图", "text_hint": "差异化卖点"},
            {"id": "summary", "name": "卖点总结", "purpose": "把前面的优势收束成购买理由", "kind": "总结图", "text_hint": "购买理由"},
        ],
    },
    {
        "id": "scene-showcase", "name": "场景展示",
        "description": "用连续场景表现商品在真实环境中的使用感受。", "recommended_count": 5,
        "modules": [
            {"id": "cover", "name": "场景开场", "purpose": "建立整体氛围", "kind": "场景图", "text_hint": "场景标题"},
            {"id": "scene-1", "name": "使用场景一", "purpose": "展示典型使用方式", "kind": "场景图", "text_hint": "使用时刻"},
            {"id": "scene-2", "name": "使用场景二", "purpose": "展示另一种生活场景", "kind": "场景图", "text_hint": "生活方式"},
            {"id": "detail", "name": "场景细节", "purpose": "用近景补充真实感", "kind": "细节图", "text_hint": "细节亮点"},
            {"id": "ending", "name": "场景收尾", "purpose": "留下统一的品牌印象", "kind": "品牌图", "text_hint": "品牌主张"},
        ],
    },
    {
        "id": "detail-closeup", "name": "细节放大",
        "description": "适合材质、工艺、接口、纹理等需要看清细节的商品。", "recommended_count": 4,
        "modules": [
            {"id": "overview", "name": "整体展示", "purpose": "先确认商品整体形态", "kind": "商品主图", "text_hint": "整体外观"},
            {"id": "detail-1", "name": "关键细节一", "purpose": "放大最重要的材质或结构", "kind": "细节图", "text_hint": "细节名称"},
            {"id": "detail-2", "name": "关键细节二", "purpose": "补充另一处细节", "kind": "细节图", "text_hint": "细节名称"},
            {"id": "craft", "name": "工艺总结", "purpose": "把细节转化成用户能理解的价值", "kind": "信息图", "text_hint": "工艺优势"},
        ],
    },
    {
        "id": "how-to-use", "name": "使用步骤",
        "description": "把商品使用过程拆成易懂的步骤，适合工具和操作类商品。", "recommended_count": 5,
        "modules": [
            {"id": "prepare", "name": "使用前准备", "purpose": "说明开始前需要准备什么", "kind": "步骤图", "text_hint": "准备"},
            {"id": "step-1", "name": "第一步", "purpose": "展示第一步操作", "kind": "步骤图", "text_hint": "步骤一"},
            {"id": "step-2", "name": "第二步", "purpose": "展示第二步操作", "kind": "步骤图", "text_hint": "步骤二"},
            {"id": "tips", "name": "使用提示", "purpose": "补充容易忽略的注意事项", "kind": "信息图", "text_hint": "小贴士"},
            {"id": "result", "name": "使用结果", "purpose": "展示完成后的状态", "kind": "结果图", "text_hint": "完成效果"},
        ],
    },
    {
        "id": "comparison", "name": "对比展示",
        "description": "用清晰的前后或不同方案对比说明商品价值。", "recommended_count": 4,
        "modules": [
            {"id": "cover", "name": "商品亮相", "purpose": "说明本次对比的对象", "kind": "商品主图", "text_hint": "对比主题"},
            {"id": "before", "name": "使用前", "purpose": "展示未使用时的状态", "kind": "对比图", "text_hint": "使用前"},
            {"id": "after", "name": "使用后", "purpose": "展示合理使用后的状态", "kind": "对比图", "text_hint": "使用后"},
            {"id": "reason", "name": "差异说明", "purpose": "解释差异来自什么功能或设计", "kind": "信息图", "text_hint": "差异原因"},
        ],
    },
    {
        "id": "brand-story", "name": "品牌故事",
        "description": "把商品、品牌理念和使用场景串成一套有气质的视觉内容。", "recommended_count": 4,
        "modules": [
            {"id": "hero", "name": "品牌主视觉", "purpose": "建立统一的第一印象", "kind": "品牌图", "text_hint": "品牌主张"},
            {"id": "origin", "name": "品牌理念", "purpose": "讲清品牌想解决的问题", "kind": "故事图", "text_hint": "品牌理念"},
            {"id": "product", "name": "商品与理念", "purpose": "把商品特点和品牌理念连接起来", "kind": "商品图", "text_hint": "设计细节"},
            {"id": "closing", "name": "品牌收尾", "purpose": "形成完整的品牌记忆点", "kind": "品牌图", "text_hint": "品牌寄语"},
        ],
    },
    {
        "id": "care-notice", "name": "售后说明",
        "description": "用简洁清楚的画面说明使用、保养和售后信息。", "recommended_count": 4,
        "modules": [
            {"id": "promise", "name": "服务承诺", "purpose": "先建立可靠、清楚的服务印象", "kind": "品牌图", "text_hint": "服务承诺"},
            {"id": "care", "name": "使用保养", "purpose": "说明如何正确使用和保养", "kind": "信息图", "text_hint": "保养方法"},
            {"id": "notice", "name": "注意事项", "purpose": "集中展示需要留意的内容", "kind": "信息图", "text_hint": "注意事项"},
            {"id": "contact", "name": "联系说明", "purpose": "留下清晰的咨询和售后提示", "kind": "收尾图", "text_hint": "联系我们"},
        ],
    },
]
DETAIL_TEMPLATE_MAP = {item["id"]: item for item in DETAIL_TEMPLATES}
TASK_DONE = {"succeeded", "failed", "cancelled"}
RUN_DONE = {"succeeded", "partial", "failed", "cancelled"}
RISK_WORDS = ("治疗", "治愈", "减肥", "根治", "百分百", "100%", "绝对", "最强", "第一", "永久")
OUTPUT_KIND_INFO = {
    "detail": {"label": "详情页", "template_id": "basic-detail", "default_count": 6},
    "main": {"label": "商品主图", "template_id": "", "default_count": 6},
    "video": {"label": "商品视频", "template_id": "", "default_count": 1},
}
CREATIVE_ACTIONS = {
    "create": "根据选中的素材生成新的创作方案",
    "variation": "保留主体与核心构图，生成一组有变化的方案",
    "background": "保留主体，替换为更合适的背景和场景",
    "expand": "保留原图内容，向画面外扩展构图和背景",
    "refine": "针对选中的内容做局部修改和细节优化",
    "continue": "沿着当前画布的风格继续创作下一组内容",
}

# 每个详情模块都要有明确的视觉任务，避免只更换模块标题却生成近似画面。
DETAIL_VISUAL_DIRECTIONS = {
    "cover": "正面或三分之二正面英雄构图，商品占画面约 55% 至 70%，背景简洁，主体放在视觉中心并留出标题留白",
    "selling-point": "商品处于真实使用场景中，采用中景或斜侧角度，用道具和光线表现核心卖点，主体放在画面一侧并留出另一侧排版空间",
    "detail": "近距离微距细节构图，只突出一个关键材质、接口、纹理或工艺区域，背景虚化，商品整体不要占满画面",
    "use": "生活化场景构图，采用横向或斜向视角展示商品如何被使用，加入合理环境和动作线索，但不添加无法确认的人物或配件",
    "spec": "干净的信息展示构图，商品缩小放在一侧，另一侧保留大面积纯净留白用于参数排版，使用平视角度和均匀光线",
    "after-sale": "品牌收尾构图，商品以小比例放在下方或角落，使用统一品牌氛围、柔和背景和充足留白，画面与首图明显不同",
}


class BrandPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    logo: str = ""
    primary_color: str = "#13b8a6"
    secondary_color: str = "#69c7ff"
    font: str = ""
    title_style: str = ""
    background_style: str = ""
    audience: str = ""
    forbidden_words: List[str] = []
    forbidden_visuals: List[str] = []
    approved_references: List[str] = []


class ParsePayload(BaseModel):
    request_text: str = ""
    platforms: List[str] = []
    output_kind: str = "auto"


class AnalyzePayload(BaseModel):
    input_snapshot: List[Dict[str, Any]] = []
    request_text: str = ""
    action: str = "create"


class DetailPlanPayload(BaseModel):
    input_snapshot: List[Dict[str, Any]] = []
    request_text: str = ""
    template_id: str = "basic-detail"
    module_ids: List[str] = []


class RunPayload(BaseModel):
    canvas_id: str = ""
    node_id: str = ""
    canvas_kind: str = "classic"
    selected_node_ids: List[str] = []
    input_snapshot: List[Dict[str, Any]] = []
    brand_profile_id: str = ""
    platforms: List[str] = ["canvas"]
    provider_id: str = ""
    model: str = ""
    request_text: str = ""
    action: str = "create"
    size: str = ""
    quality: str = "auto"
    fidelity: str = "strict"
    add_text: bool = True
    max_retries: int = 2
    dry_run: bool = False
    template_id: str = ""
    template_name: str = ""
    detail_modules: List[Dict[str, Any]] = []
    template_version: str = "1"
    output_kind: str = "auto"
    video_duration: int = 5
    aspect_ratio: str = "16:9"
    resolution: str = ""


def normalize_output_kind(value: str) -> str:
    value = str(value or "").strip().lower()
    return value if value in OUTPUT_KIND_INFO else "auto"


def explicit_output_kind(text: str) -> str:
    """Return a kind explicitly named by the request, ignoring stale UI state."""
    text = str(text or "").strip()
    if re.search(r"视频|短视频|宣传片|广告片|商品片", text, re.I):
        return "video"
    if re.search(r"详情页|详情图|详情页面|详情", text, re.I):
        return "detail"
    if re.search(r"主图|白底图|商品图|产品图|电商图|套图", text, re.I):
        return "main"
    return ""


def detect_output_kind(text: str, requested: str = "auto") -> Dict[str, Any]:
    requested = normalize_output_kind(requested)
    explicit = explicit_output_kind(text)
    if explicit:
        info = OUTPUT_KIND_INFO[explicit]
        source = "text_override" if requested not in {"auto", explicit} else "text"
        return {"kind": explicit, **info, "source": source}
    if requested != "auto":
        return {"kind": requested, **OUTPUT_KIND_INFO[requested], "source": "manual"}
    text = str(text or "").strip()
    # 明确写出视频时优先走视频接口，避免“视频主图”被当成图片任务。
    if re.search(r"视频|短视频|宣传片|广告片|商品片", text, re.I):
        kind = "video"
    elif re.search(r"详情页|详情图|详情页面|详情", text, re.I):
        kind = "detail"
    elif re.search(r"主图|白底图|商品图|产品图|电商图|套图", text, re.I):
        kind = "main"
    else:
        kind = "main"
    return {"kind": kind, **OUTPUT_KIND_INFO[kind], "source": "text"}


def parse_quantity(text: str, platforms=None, output_kind: str = "auto") -> Dict[str, Any]:
    text = str(text or "").strip()
    output = detect_output_kind(text, output_kind)
    kind = output["kind"]
    warnings = []
    explicit = re.search(r"总(?:共|计)?\s*(\d+)\s*张", text)
    page_each = re.search(r"(\d+)\s*页[^\d]{0,12}(?:每页|一页)\s*(\d+)\s*张", text)
    page = re.search(r"(\d+)\s*页", text)
    images = re.search(r"(?:生成|制作|做|要)?\s*(\d+)\s*张", text)
    videos = re.search(r"(?:生成|制作|做|要)?\s*(\d+)\s*(?:条|个)\s*视频", text)
    pages = int(page_each.group(1)) if page_each else (int(page.group(1)) if page else 0)
    each = int(page_each.group(2)) if page_each else 0
    calculated = pages * each if pages and each else 0
    if explicit:
        total, source = int(explicit.group(1)), "explicit_total"
        if calculated and calculated != total:
            warnings.append(f"数量有冲突：页数计算为 {calculated} 张，按明确的总共 {total} 张执行")
    elif calculated:
        total, source = calculated, "pages_times_each"
    elif pages:
        total, each, source = pages, 1, "pages"
    elif videos and kind == "video":
        total, source = int(videos.group(1)), "videos"
    elif images:
        total, source = int(images.group(1)), "images"
    else:
        total = int(output["default_count"])
        source = "automatic"
        unit = "条" if kind == "video" else "张"
        warnings.append(f"没有写明数量，已自动规划 {total} {unit}")
    if total > 200:
        total = 200
        warnings.append("单次最多规划 200 张，已按 200 张处理")
    total = max(1, total)
    pages = pages or total
    each = each or max(1, (total + pages - 1) // pages)
    return {
        "page_count": pages, "images_per_page": each, "total_images": total,
        "quantity_source": source, "warnings": warnings,
        "batches": [min(20, total - start) for start in range(0, total, 20)],
        "output_kind": kind, "output_label": output["label"],
    }


def _node_text(node):
    for key in ("text", "prompt", "content", "title", "name"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _node_images(node):
    urls = []
    for key in ("url", "image", "src"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
    for item in node.get("images") or []:
        value = item if isinstance(item, str) else item.get("url") or item.get("src") if isinstance(item, dict) else ""
        if str(value or "").strip():
            urls.append(str(value).strip())
    return list(dict.fromkeys(urls))


def _product(snapshot):
    texts = [text for text in (_node_text(node) for node in snapshot) if text]
    refs = list(dict.fromkeys(url for node in snapshot for url in _node_images(node)))[:20]
    name = texts[0].splitlines()[0][:80] if texts else "未命名创作"
    return {
        "name": name, "category": "待结合图片确认", "known_facts": texts[:20],
        "inferred_claims": [] if texts else ["商品名称和参数未提供，需要结合图片判断"],
        "reference_images": refs, "source_image_count": len(refs),
        "protected_elements": ["Logo", "包装文字", "商品颜色", "商品结构", "商品数量"],
        "uncertainties": [] if texts else ["商品名称", "商品参数", "核心卖点"],
    }


def _agent_analysis(snapshot, request_text="", action="create"):
    """Build a local, explainable plan before any paid image request."""
    snapshot = [item for item in snapshot if isinstance(item, dict)]
    texts = [text for text in (_node_text(node) for node in snapshot) if text]
    images = list(dict.fromkeys(url for node in snapshot for url in _node_images(node)))
    action = action if action in CREATIVE_ACTIONS else "create"
    steps = [
        "读取当前选中的图片、文字和参考素材",
        "保留主体、Logo、原有文字和关键结构",
        CREATIVE_ACTIONS[action],
        "把生成结果作为新节点追加回当前画布",
    ]
    warnings = []
    if not images:
        warnings.append("当前选中内容没有图片，生成图片前请至少选中一张图片")
    if not texts:
        warnings.append("当前没有文字说明，Agent 会只根据参考图片进行创作")
    if any(word in str(request_text or "") for word in RISK_WORDS):
        warnings.append("指令中包含需要人工核实的宣传词")
    return {
        "source_count": len(snapshot),
        "image_count": len(images),
        "text_count": len(texts),
        "known_text": texts[:8],
        "protected_elements": ["主体外观", "Logo", "原有文字", "颜色和结构"],
        "action": action,
        "action_label": CREATIVE_ACTIONS[action],
        "steps": steps,
        "warnings": warnings,
        "ready": bool(images),
    }


def _detail_template(template_id):
    return DETAIL_TEMPLATE_MAP.get(str(template_id or "").strip()) or DETAIL_TEMPLATE_MAP["basic-detail"]


def _detail_plan(snapshot, request_text="", template_id="basic-detail", module_ids=None):
    template = _detail_template(template_id)
    requested = set(str(item) for item in (module_ids or []) if item)
    modules = [item for item in template["modules"] if not requested or item["id"] in requested]
    if not modules:
        modules = list(template["modules"])
    quantity = parse_quantity(request_text, ["canvas"])
    total = quantity["total_images"] if quantity["quantity_source"] != "automatic" else len(modules)
    rows = []
    for index in range(total):
        module = modules[index % len(modules)]
        rows.append({
            "index": index + 1, "page": index + 1, "module_id": module["id"],
            "module_name": module["name"], "purpose": module["purpose"],
            "kind": module["kind"], "text_hint": module["text_hint"],
            "prompt": (
                f"为选中的商品制作“{module['name']}”详情页模块，目标是{module['purpose']}。"
                f"画面类型：{module['kind']}；建议文字：{module['text_hint']}。"
                + (f"本次创作要求：{str(request_text).strip()}。" if str(request_text).strip() else "")
                + "严格保持商品外观、Logo、包装文字、颜色、比例、结构和数量不变，"
                + "只生成干净背景、合理场景、自然光影和清晰留白，不直接生成中文、价格或水印。"
            ),
        })
    return {
        "template_id": template["id"], "template_name": template["name"],
        "template_description": template["description"],
        "recommended_count": template["recommended_count"], "total_images": total,
        "modules": rows, "module_library": modules,
        "steps": ["确定首屏和详情模块顺序", "为每个模块匹配选中的商品素材",
                   "生成干净底图和可编辑文字层", "完成后可逐张打开查看并放回画布"],
    }


def _plans(run):
    purposes = ("方案一", "方案二", "方案三", "方案四", "细节优化", "构图变化", "场景变化", "继续创作")
    name = run["product_profile"]["name"]
    brand = run.get("brand_profile") or {}
    brand_note = ""
    if brand:
        brand_note = (
            f"品牌为{brand.get('name') or '未命名品牌'}，主色{brand.get('primary_color') or '未指定'}，"
            f"辅助色{brand.get('secondary_color') or '未指定'}，目标人群{brand.get('audience') or '未指定'}。"
        )
    forbidden = "、".join(brand.get("forbidden_words") or [])
    result = []
    detail_modules = run.get("detail_modules") or []
    for index in range(run["total_images"]):
        platform = run["platforms"][index % len(run["platforms"])]
        spec, purpose = PLATFORMS[platform], purposes[index % len(purposes)]
        media_kind = "video" if run.get("output_kind") == "video" else "image"
        page = min(run["page_count"], index // max(1, run["images_per_page"]) + 1)
        module = detail_modules[index % len(detail_modules)] if detail_modules else {}
        module_name = module.get("module_name") or ""
        module_purpose = module.get("purpose") or ""
        module_id = module.get("module_id") or ""
        visual_direction = DETAIL_VISUAL_DIRECTIONS.get(
            module_id,
            (
                "近景或斜侧角度，突出一个可确认的局部特点，背景适度虚化"
                if "细节" in str(module.get("kind") or "") or "细节" in module_name
                else "采用与其他图片明显不同的镜头角度、主体位置、背景层次和留白方式"
            ),
        )
        action_note = CREATIVE_ACTIONS.get(run.get("action") or "create", CREATIVE_ACTIONS["create"])
        prompt = (
            f"在无限画布中为{name}进行{action_note}，当前方向是{purpose}。{spec['focus']}。{brand_note}"
            + (f"这是详情页的“{module_name}”模块，目标是{module_purpose}。" if module_name else "")
            + (f"本张专用视觉方案：{visual_direction}。" if module_name else "")
            + (
                f"请制作一条约{run.get('video_duration') or 5}秒的商品展示短视频，"
                f"画面比例为{run.get('aspect_ratio') or '16:9'}，镜头平稳，主体始终清楚可见。"
                if media_kind == "video" else ""
            )
            + f"这是第 {index + 1} 张，必须和同一套详情页的其他图片形成明显差异，不要复用其他图片的镜头、主体位置或背景。"
            + "严格保留参考商品的Logo、包装文字、颜色、比例、结构和数量，不重画有文字的包装正面，"
            "不得虚构配件。只生成干净背景、场景和自然光影，不生成中文、价格或水印，"
            "为后续继续编辑保留清晰留白。主体清晰，边缘自然，画面有商业创作质感。"
            + (f"不得出现这些禁用词或相关文字：{forbidden}。" if forbidden else "")
        )
        result.append({
            "id": f"plan_{index + 1:03d}", "index": index + 1, "page": page,
            "platform": platform, "platform_label": spec["label"], "purpose": purpose,
            "size": run.get("size") or spec["size"], "prompt": prompt,
            "title": f"{name} · {module_name or purpose}", "subtitle": module_purpose or spec["focus"],
            "module_id": module.get("module_id") or "", "module_name": module_name,
            "module_kind": module.get("kind") or "", "text_hint": module.get("text_hint") or "",
            "media_kind": media_kind,
        })
    return result


def register_ecommerce_agent(app, *, base_dir, submit_image_task, get_image_task,
                              cancel_image_task, public_providers, estimate_cost=None,
                              submit_video_task=None):
    def choose_state_root():
        """Prefer the project data directory, but keep first-run Agent usable in a read-only folder."""
        preferred = Path(base_dir) / "data" / "ecommerce"
        candidates = [preferred]
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "XiaoQiAI" / "data" / "ecommerce")
        else:
            candidates.append(Path.home() / "XiaoQiAI" / "data" / "ecommerce")
        last_error = None
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / f".write-check-{uuid.uuid4().hex}"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                return candidate
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"画布 Agent 数据目录不可写，请把项目解压到有写入权限的文件夹：{last_error}")

    root = choose_state_root()
    brand_dir, product_dir = root / "brands", root / "products"
    run_dir, export_dir = root / "runs", root / "exports"
    for path in (brand_dir, product_dir, run_dir, export_dir):
        path.mkdir(parents=True, exist_ok=True)
    lock, workers, run_locks = RLock(), {}, {}

    def safe_id(value):
        value = re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))
        if not value:
            raise HTTPException(status_code=400, detail="记录编号不合法")
        return value

    def atomic(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

    def read(path, default=None):
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

    def run_path(run_id):
        return run_dir / f"{safe_id(run_id)}.json"

    def load_run(run_id):
        run = read(run_path(run_id))
        if not isinstance(run, dict):
            raise HTTPException(status_code=404, detail="画布 Agent 任务不存在")
        return run

    def save(run):
        run["updated_at"] = time.time()
        with lock:
            atomic(run_path(run["id"]), run)
        return run

    def run_async_lock(run_id):
        return run_locks.setdefault(run_id, asyncio.Lock())

    async def mutate_run(run_id, output_id=None, changes=None, run_changes=None):
        """Merge one output into the latest file so concurrent completions cannot overwrite each other."""
        async with run_async_lock(run_id):
            current = load_run(run_id)
            output = None
            if output_id:
                output = next((item for item in current.get("outputs") or [] if item.get("id") == output_id), None)
                if not output:
                    raise RuntimeError("画布图片任务不存在")
                if callable(changes):
                    changes(current, output)
                elif changes:
                    output.update(changes)
            if run_changes:
                current.update(run_changes)
            save(current)
            return current, output

    def summarize(run):
        outputs = run.get("outputs") or []
        run["success_count"] = sum(item.get("status") == "succeeded" for item in outputs)
        run["failed_count"] = sum(item.get("status") == "failed" for item in outputs)
        run["cancelled_count"] = sum(item.get("status") == "cancelled" for item in outputs)
        run["retry_count"] = sum(int(item.get("retry_count") or 0) for item in outputs)
        costs = [float((item.get("cost") or {}).get("amount") or 0) for item in outputs]
        run["actual_cost"] = round(sum(costs), 6) if any(costs) else None
        done = run["success_count"] + run["failed_count"] + run["cancelled_count"]
        run["progress"] = round(done * 100 / max(1, run["total_images"]), 1)

    def result_cost(task):
        result = task.get("result") or {}
        cost = result.get("generation_cost") or {}
        if isinstance(cost, (int, float)):
            return {"amount": float(cost), "currency": "CNY", "source": "upstream"}
        if isinstance(cost, dict):
            amount = cost.get("amount", cost.get("cost", cost.get("total")))
            try:
                return {**cost, "amount": float(amount)} if amount is not None else cost
            except Exception:
                return cost
        return {}

    async def wait_task(task_id, timeout_seconds=1800):
        deadline = time.monotonic() + max(60, int(timeout_seconds or 1800))
        while True:
            task = get_image_task(task_id) or {}
            if not task:
                raise RuntimeError("图片任务状态无法读取，可能服务刚刚重启。为避免重复扣费，请检查任务记录后再重试。")
            if task.get("status") in TASK_DONE:
                return task
            if time.monotonic() >= deadline:
                try:
                    cancel_image_task(task_id)
                except Exception:
                    pass
                raise RuntimeError("图片生成等待超时，任务已停止等待。请查看任务中心，确认上游没有继续生成后再重试。")
            await asyncio.sleep(0.45)

    async def execute_output(run_id, output_id):
        run = load_run(run_id)
        output = next((item for item in run["outputs"] if item["id"] == output_id), None)
        if not output:
            return
        limit = max(0, min(2, int(run.get("max_retries") or 0)))
        while True:
            run = load_run(run_id)
            output = next(item for item in run["outputs"] if item["id"] == output_id)
            if run.get("cancel_requested"):
                await mutate_run(run_id, output_id, {"status": "cancelled"})
                return
            while run.get("pause_requested"):
                await mutate_run(run_id, run_changes={"status": "paused", "current_stage": "已暂停"})
                await asyncio.sleep(0.5)
                run = load_run(run_id)
                output = next(item for item in run["outputs"] if item["id"] == output_id)
            plan = output["plan"]
            refs = [{"url": url, "name": f"商品参考图{i + 1}", "role": "商品主体", "kind": "image"}
                    for i, url in enumerate(run["product_profile"]["reference_images"])]
            run, output = await mutate_run(
                run_id, output_id, {"status": "queued", "started_at": time.time(), "error": ""},
                {"status": "generating", "current_stage": ("生成视频" if plan.get("media_kind") == "video" else "生成图片") + f" {plan['index']}/{run['total_images']}"},
            )
            try:
                if plan.get("media_kind") == "video":
                    if not submit_video_task:
                        raise RuntimeError("当前分享包未包含视频 Agent 组件，请重新制作完整分享包")
                    submitted = await submit_video_task({
                        "prompt": plan["prompt"], "provider_id": run["provider_id"],
                        "model": run["model"], "duration": run.get("video_duration") or 5,
                        "aspect_ratio": run.get("aspect_ratio") or "16:9",
                        "resolution": run.get("resolution") or "",
                        "images": refs, "enhance_prompt": False,
                        "enable_upsample": False, "watermark": False,
                        "generate_audio": False, "multimodal": False,
                    })
                    urls = (submitted.get("videos") or submitted.get("video_urls")
                            or submitted.get("urls") or submitted.get("video") or [])
                    if isinstance(urls, str):
                        urls = [urls]
                    if not urls:
                        raise RuntimeError("上游视频任务完成但没有返回视频")
                    cost = result_cost({"result": submitted})
                    await mutate_run(run_id, output_id, {
                        "status": "succeeded", "url": urls[0], "urls": urls,
                        "media_kind": "video", "upstream_task_id": submitted.get("task_id") or submitted.get("request_id") or "",
                        "cost": cost, "cost_status": submitted.get("generation_cost_status") or {},
                        "quality_status": "needs_review",
                        "quality_checks": {"video_returned": True, "duration_requested": run.get("video_duration") or 5},
                        "completed_at": time.time(), "error": "",
                    })
                    return
                submitted = await submit_image_task({
                    "prompt": plan["prompt"], "provider_id": run["provider_id"], "model": run["model"],
                    "size": plan["size"], "quality": run.get("quality") or "auto", "n": 1,
                    "reference_images": refs, "canvas_id": run.get("canvas_id") or "",
                    "node_id": run.get("node_id") or "",
                    "task_label": f"画布 Agent · {plan['purpose']}",
                })
                run, output = await mutate_run(run_id, output_id, {"task_id": submitted["task_id"], "status": "running"})
                task = await wait_task(output["task_id"])
                if task.get("status") != "succeeded":
                    raise RuntimeError(task.get("error") or "图片生成失败")
                result = task.get("result") or {}
                urls = result.get("images") or []
                if not urls:
                    raise RuntimeError("上游任务完成但没有返回图片")
                await mutate_run(run_id, output_id, {
                    "status": "succeeded", "url": urls[0], "image_items": result.get("image_items") or [],
                    "media_kind": "image",
                    "upstream_task_id": result.get("task_id") or result.get("request_id") or "",
                    "cost": result_cost(task), "cost_status": result.get("generation_cost_status") or {},
                    "quality_status": "needs_review",
                    "quality_checks": {"image_returned": True, "size_requested": plan["size"],
                        "visual_fidelity": "需要人工确认商品、Logo与包装文字一致性",
                        "text_layer": "底图不含中文，中文由可编辑文字层提供"},
                    "text_layers": ([{"type": "title", "text": plan["title"], "editable": True},
                                     {"type": "selling_point", "text": plan["subtitle"], "editable": True}]
                                    if run.get("add_text") else []),
                    "completed_at": time.time(), "error": "",
                })
                return
            except Exception as exc:
                detail = str(getattr(exc, "detail", "") or exc)
                def record_failure(_run, latest):
                    latest["retry_count"] = int(latest.get("retry_count") or 0) + 1
                    latest["error"] = detail
                    latest["status"] = "failed" if latest["retry_count"] > limit else "retrying"
                    if latest["status"] == "failed":
                        latest["completed_at"] = time.time()
                run, output = await mutate_run(run_id, output_id, record_failure)
                if output["status"] == "failed":
                    return
                await asyncio.sleep(0.8)

    async def worker(run_id):
        try:
            run = load_run(run_id)
            if run.get("dry_run"):
                run.update({"status": "succeeded", "current_stage": "方案预演完成", "progress": 100.0,
                            "completed_at": time.time(), "success_count": 0, "failed_count": 0})
                save(run)
                return
            run.update({"status": "planning", "current_stage": "规划创作内容与生成批次", "progress": 3.0})
            save(run)
            # Images enter the existing task-center queue in batches of 20. Video calls are synchronous
            # in the current provider adapters, so keep their Agent concurrency deliberately small.
            batch_size = 2 if run.get("output_kind") == "video" else 20
            for start in range(0, len(run["outputs"]), batch_size):
                run = load_run(run_id)
                if run.get("cancel_requested"):
                    break
                batch = [item for item in run["outputs"][start:start + batch_size] if item.get("status") in {"waiting", "retrying"}]
                await asyncio.gather(*(execute_output(run_id, item["id"]) for item in batch))
                run = load_run(run_id)
                summarize(run)
                save(run)
            run = load_run(run_id)
            for item in run["outputs"]:
                if run.get("cancel_requested") and item.get("status") == "waiting":
                    item["status"] = "cancelled"
            summarize(run)
            if run.get("cancel_requested"):
                status = "cancelled"
            elif run["success_count"] and run["failed_count"]:
                status = "partial"
            elif run["failed_count"]:
                status = "failed"
            else:
                status = "succeeded"
            run.update({"status": status, "current_stage": {"succeeded": "已完成", "partial": "部分完成",
                "cancelled": "已取消", "failed": "失败"}[status], "completed_at": time.time()})
            if status != "cancelled":
                run["progress"] = 100.0
            save(run)
        except Exception as exc:
            try:
                run = load_run(run_id)
                run.update({"status": "failed", "current_stage": "运行失败",
                            "errors": (run.get("errors") or []) + [str(exc)]})
                save(run)
            except Exception:
                pass
        finally:
            workers.pop(run_id, None)

    def start(run_id):
        if run_id not in workers or workers[run_id].done():
            workers[run_id] = asyncio.create_task(worker(run_id))

    @app.get("/api/ecommerce-agent/platforms")
    async def platforms_api():
        # 新版只展示无限画布创作通道；旧平台字段保留在后端，确保历史任务仍能读取。
        return {"platforms": [{"id": "canvas", **PLATFORMS["canvas"]}],
                "providers": public_providers()}

    @app.get("/api/ecommerce-agent/health")
    async def health_api():
        """A no-secret diagnostic endpoint used by the launcher and the Agent panel."""
        try:
            providers = public_providers()
        except Exception as exc:
            return {
                "ok": False,
                "storage_ok": root.exists(),
                "storage_root": str(root),
                "provider_count": 0,
                "image_provider_count": 0,
                "video_provider_count": 0,
                "message": f"API 配置读取失败：{exc}",
            }
        image_providers = [item for item in providers if item.get("enabled", True) and item.get("image_models")]
        video_providers = [item for item in providers if item.get("enabled", True) and item.get("video_models")]
        return {
            "ok": True,
            "storage_ok": root.exists(),
            "storage_root": str(root),
            "provider_count": len(providers),
            "image_provider_count": len(image_providers),
            "video_provider_count": len(video_providers),
            "feature_flags": {"detail": True, "main": True, "video": bool(submit_video_task)},
            "message": "画布 Agent 已就绪",
        }

    @app.get("/api/ecommerce-agent/brands")
    async def brands_api():
        rows = [read(path, {}) for path in brand_dir.glob("*.json")]
        return {"brands": sorted([row for row in rows if row], key=lambda row: row.get("updated_at", 0), reverse=True)}

    @app.post("/api/ecommerce-agent/brands")
    async def create_brand(payload: BrandPayload):
        now = time.time()
        row = {"id": f"brand_{uuid.uuid4().hex}", **payload.dict(), "created_at": now, "updated_at": now}
        atomic(brand_dir / f"{row['id']}.json", row)
        return {"brand": row}

    @app.put("/api/ecommerce-agent/brands/{brand_id}")
    async def update_brand(brand_id: str, payload: BrandPayload):
        path = brand_dir / f"{safe_id(brand_id)}.json"
        old = read(path)
        if not old:
            raise HTTPException(status_code=404, detail="品牌档案不存在")
        row = {**old, **payload.dict(), "updated_at": time.time()}
        atomic(path, row)
        return {"brand": row}

    @app.delete("/api/ecommerce-agent/brands/{brand_id}")
    async def delete_brand(brand_id: str):
        path = brand_dir / f"{safe_id(brand_id)}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="品牌档案不存在")
        path.unlink()
        return {"ok": True}

    @app.post("/api/ecommerce-agent/parse-request")
    async def parse_api(payload: ParsePayload):
        selected = [item for item in payload.platforms if item in PLATFORMS] or ["canvas"]
        quantity = parse_quantity(payload.request_text, selected, payload.output_kind)
        detected = detect_output_kind(payload.request_text, payload.output_kind)
        return {"quantity": quantity, "output": detected,
                "platforms": [{"id": item, **PLATFORMS[item]} for item in selected]}

    @app.post("/api/ecommerce-agent/analyze")
    async def analyze_api(payload: AnalyzePayload):
        return {"analysis": _agent_analysis(payload.input_snapshot, payload.request_text, payload.action)}

    @app.get("/api/ecommerce-agent/detail-templates")
    async def detail_templates_api():
        return {"templates": DETAIL_TEMPLATES}

    @app.post("/api/ecommerce-agent/detail-plan")
    async def detail_plan_api(payload: DetailPlanPayload):
        if not [item for item in payload.input_snapshot if isinstance(item, dict)]:
            raise HTTPException(status_code=400, detail="请先在画布中选中商品图片或说明文字")
        plan = _detail_plan(payload.input_snapshot, payload.request_text, payload.template_id, payload.module_ids)
        plan["analysis"] = _agent_analysis(payload.input_snapshot, payload.request_text, "create")
        return {"plan": plan}

    @app.get("/api/ecommerce-agent/runs")
    async def runs_api(canvas_id: str = "", limit: int = 30):
        rows = [read(path, {}) for path in run_dir.glob("*.json")]
        rows = [row for row in rows if row and (not canvas_id or row.get("canvas_id") == canvas_id)]
        rows.sort(key=lambda row: row.get("created_at", 0), reverse=True)
        return {"runs": rows[:max(1, min(100, limit))]}

    @app.post("/api/ecommerce-agent/runs")
    async def create_run(payload: RunPayload):
        selected_platforms = list(dict.fromkeys(item for item in payload.platforms if item in PLATFORMS)) or ["canvas"]
        snapshot = [dict(item) for item in payload.input_snapshot if isinstance(item, dict)]
        if not snapshot:
            raise HTTPException(status_code=400, detail="请先在画布中选中商品图片或说明文字")
        product = _product(snapshot)
        if not product["reference_images"]:
            raise HTTPException(status_code=400, detail="选中的节点里没有商品图片，请至少选择一张商品图")
        detected = detect_output_kind(payload.request_text, payload.output_kind)
        output_kind = detected["kind"]
        if not payload.dry_run:
            providers = [item for item in public_providers() if item.get("enabled", True)]
            provider_ids = {str(item.get("id") or "") for item in providers}
            if payload.provider_id not in provider_ids:
                raise HTTPException(status_code=400, detail="请选择已经配置好的 API")
            if not payload.model:
                raise HTTPException(status_code=400, detail="请选择生成模型")
            provider = next((item for item in providers if item.get("id") == payload.provider_id), {})
            model_list = provider.get("video_models") or [] if output_kind == "video" else provider.get("image_models") or []
            if payload.model not in model_list:
                kind_label = "视频" if output_kind == "video" else "图片"
                raise HTTPException(status_code=400, detail=f"所选 API 未配置“{payload.model}”{kind_label}模型，请刷新 API 设置后重试")
        quantity, now = parse_quantity(payload.request_text, selected_platforms, output_kind), time.time()
        detail = _detail_plan(snapshot, payload.request_text, payload.template_id,
                              [item.get("module_id") for item in payload.detail_modules]) if payload.template_id else None
        if detail and detail.get("total_images"):
            quantity = {**quantity, "total_images": detail["total_images"],
                        "page_count": detail["total_images"], "images_per_page": 1,
                        "quantity_source": "detail_template",
                        "batches": [min(20, detail["total_images"] - start)
                                    for start in range(0, detail["total_images"], 20)]}
        if output_kind == "detail" and not payload.template_id:
            detail = _detail_plan(snapshot, payload.request_text, "basic-detail")
            quantity = {**quantity, "total_images": detail["total_images"],
                        "page_count": detail["total_images"], "images_per_page": 1,
                        "quantity_source": "detail_template",
                        "batches": [min(20, detail["total_images"] - start)
                                    for start in range(0, detail["total_images"], 20)]}
        brand_profile = read(brand_dir / f"{safe_id(payload.brand_profile_id)}.json", {}) if payload.brand_profile_id else {}
        estimated = estimate_cost(payload.provider_id, payload.model, quantity["total_images"], "video" if output_kind == "video" else "image") if estimate_cost and not payload.dry_run else None
        run = {
            "id": f"ecrun_{uuid.uuid4().hex}", "canvas_id": payload.canvas_id, "node_id": payload.node_id,
            "canvas_kind": payload.canvas_kind, "selected_node_ids": payload.selected_node_ids,
            "input_snapshot": snapshot, "brand_profile_id": payload.brand_profile_id, "brand_profile": brand_profile,
            "platforms": selected_platforms, "provider_id": payload.provider_id, "model": payload.model,
            "request_text": payload.request_text, "action": payload.action if payload.action in CREATIVE_ACTIONS else "create",
            "output_kind": output_kind, "output_label": detected["label"],
            "video_duration": max(1, min(60, int(payload.video_duration or 5))),
            "aspect_ratio": payload.aspect_ratio or "16:9", "resolution": payload.resolution or "",
            "size": payload.size, "quality": payload.quality,
            "fidelity": payload.fidelity, "add_text": payload.add_text,
            "template_id": payload.template_id, "template_name": payload.template_name,
            "detail_modules": payload.detail_modules, "template_version": payload.template_version,
            "max_retries": max(0, min(2, payload.max_retries)), "dry_run": payload.dry_run,
            **quantity, "product_profile": product, "status": "queued", "current_stage": "等待执行",
            "progress": 0.0, "estimated_cost": (estimated or {}).get("amount") if isinstance(estimated, dict) else None,
            "estimated_cost_detail": estimated or {}, "actual_cost": None,
            "warnings": quantity["warnings"] + (["检测到高风险宣传词，导出前请核实"] if any(word in payload.request_text for word in RISK_WORDS) else []),
            "errors": [], "inferred_claims": product["inferred_claims"],
            "agent_analysis": _agent_analysis(snapshot, payload.request_text, payload.action),
            "pause_requested": False, "cancel_requested": False, "created_at": now, "updated_at": now,
        }
        if detail and not payload.detail_modules:
            run["detail_modules"] = detail.get("modules") or []
            run["template_id"] = detail.get("template_id") or run.get("template_id")
            run["template_name"] = detail.get("template_name") or run.get("template_name")
        run["visual_plans"] = _plans(run)
        run["outputs"] = [{"id": f"out_{uuid.uuid4().hex}", "status": "waiting", "retry_count": 0, "plan": plan}
                          for plan in run["visual_plans"]]
        save(run)
        start(run["id"])
        return {"run": run}

    @app.get("/api/ecommerce-agent/runs/{run_id}")
    async def get_run_api(run_id: str):
        return {"run": load_run(run_id)}

    @app.post("/api/ecommerce-agent/runs/{run_id}/pause")
    async def pause_api(run_id: str):
        run = load_run(run_id)
        if run.get("status") in RUN_DONE:
            raise HTTPException(status_code=409, detail="已结束的任务不能暂停")
        run.update({"pause_requested": True, "current_stage": "正在暂停，已提交的图片会继续完成"})
        return {"run": save(run)}

    @app.post("/api/ecommerce-agent/runs/{run_id}/resume")
    async def resume_api(run_id: str):
        run = load_run(run_id)
        if run.get("status") in RUN_DONE:
            raise HTTPException(status_code=409, detail="已结束的任务不能继续")
        interrupted = [item for item in run.get("outputs") or [] if item.get("status") == "interrupted"]
        if interrupted:
            raise HTTPException(
                status_code=409,
                detail=f"有 {len(interrupted)} 张图片在服务重启前已提交。为避免重复扣费，已停止自动续传；请使用“重试失败图片”明确重新提交。",
            )
        run.update({"pause_requested": False, "status": "generating", "current_stage": "继续执行"})
        save(run)
        start(run_id)
        return {"run": run}

    @app.post("/api/ecommerce-agent/runs/{run_id}/cancel")
    async def cancel_api(run_id: str):
        run = load_run(run_id)
        run.update({"cancel_requested": True, "pause_requested": False})
        for item in run["outputs"]:
            if item.get("status") == "queued" and item.get("task_id"):
                try:
                    cancel_image_task(item["task_id"])
                    item["status"] = "cancelled"
                except Exception:
                    pass
            elif item.get("status") == "waiting":
                item["status"] = "cancelled"
        summarize(run)
        return {"run": save(run)}

    @app.post("/api/ecommerce-agent/runs/{run_id}/retry")
    async def retry_api(run_id: str):
        run = load_run(run_id)
        failed = [item for item in run["outputs"] if item.get("status") == "failed"]
        if not failed:
            raise HTTPException(status_code=409, detail="没有可重试的失败图片")
        for item in failed:
            item.update({"status": "waiting", "retry_count": 0, "error": ""})
        run.update({"status": "queued", "cancel_requested": False, "pause_requested": False, "completed_at": None})
        save(run)
        start(run_id)
        return {"run": run}

    @app.post("/api/ecommerce-agent/runs/{run_id}/retry-output/{output_id}")
    async def retry_output_api(run_id: str, output_id: str):
        run = load_run(run_id)
        output = next((item for item in run["outputs"] if item["id"] == output_id), None)
        if not output:
            raise HTTPException(status_code=404, detail="图片任务不存在")
        if output.get("status") not in {"failed", "succeeded"}:
            raise HTTPException(status_code=409, detail="当前图片仍在执行，不能重复提交")
        output.update({"status": "waiting", "retry_count": 0, "error": "", "url": ""})
        run.update({"status": "generating", "completed_at": None, "cancel_requested": False})
        save(run)
        asyncio.create_task(execute_output(run_id, output_id))
        return {"run": run}

    @app.post("/api/ecommerce-agent/runs/{run_id}/fact-only")
    async def fact_only_api(run_id: str):
        run = load_run(run_id)
        inferred = set(run.get("inferred_claims") or [])
        for item in run["outputs"]:
            item["text_layers"] = [layer for layer in item.get("text_layers") or [] if layer.get("text") not in inferred]
        run.update({"inferred_claims": [], "fact_only": True})
        return {"run": save(run)}

    def zip_media(zf, url, name):
        try:
            text = str(url or "").strip()
            if text.startswith("data:"):
                import base64
                header, encoded = text.split(",", 1)
                if ";base64" in header:
                    zf.writestr(name, base64.b64decode(encoded))
                    return
            if text.startswith("/assets/") or text.startswith("/output/"):
                source = (Path(base_dir) / text.split("?", 1)[0].lstrip("/")).resolve()
                if str(source).startswith(str(Path(base_dir).resolve())) and source.is_file():
                    zf.write(source, name)
                    return
            if re.match(r"^[a-zA-Z]:[\\/]", text):
                source = Path(text).expanduser().resolve()
                if source.is_file():
                    zf.write(source, name)
                    return
            if text.startswith(("http://", "https://")):
                response = requests.get(text, timeout=30)
                response.raise_for_status()
                zf.writestr(name, response.content)
        except Exception:
            return

    def export_name(value, fallback="未命名"):
        clean = re.sub(r"[\\/:*?\"<>|]+", "_", str(value or "").strip())
        return (clean[:80] or fallback).strip(" ._") or fallback

    def output_extension(url, media_kind="image"):
        suffix = Path(str(url or "").split("?", 1)[0]).suffix.lower()
        allowed = {".png", ".jpg", ".jpeg", ".webp"} if media_kind != "video" else {".mp4", ".webm", ".mov", ".m4v"}
        return suffix if suffix in allowed else (".mp4" if media_kind == "video" else ".png")

    @app.post("/api/ecommerce-agent/runs/{run_id}/export")
    async def export_api(run_id: str):
        run = load_run(run_id)
        product = export_name(run.get("product_profile", {}).get("name"), "创作项目")
        target = export_dir / f"{run_id}.zip"
        safe_run = {key: value for key, value in run.items() if key != "input_snapshot"}
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{product}/运行报告/run-report.json", json.dumps(safe_run, ensure_ascii=False, indent=2))
            zf.writestr(f"{product}/运行报告/inferred-claims.json", json.dumps(run.get("inferred_claims") or [], ensure_ascii=False, indent=2))
            zf.writestr(f"{product}/文案/copy.json", json.dumps([{"page": item["plan"]["page"],
                "index": item["plan"]["index"], "platform": item["plan"]["platform_label"],
                "title": item["plan"]["title"], "subtitle": item["plan"]["subtitle"],
                "text_layers": item.get("text_layers") or []} for item in run["outputs"]], ensure_ascii=False, indent=2))
            zf.writestr(f"{product}/可编辑项目/project.json", json.dumps({"schema": "xiaoqi-ecommerce-agent-v1", "run": safe_run}, ensure_ascii=False, indent=2))
            zf.writestr(f"{product}/可编辑项目/README.txt", "这是无限画布 Agent 的可编辑交付数据。\n图片底图与文字层分开保存，文字内容可在 project.json 和文案/copy.json 中继续编辑。\n当前版本不会把 API Key、.env、history.json 或其他画布数据放入交付包。\n")
            zf.writestr(f"{product}/原始母版/README.txt", "本目录保存本次运行选中的商品参考图。若原图来自本地且文件仍存在，会一并复制进来。\n")
            zf.writestr(f"{product}/最终成片/README.txt", "本次版本采用底图与可编辑中文文字层分离的交付方式。\n可直接使用的干净底图在“干净底图”目录，标题和卖点文字在“文案”目录及 project.json 中。\n")
            for index, url in enumerate(run.get("product_profile", {}).get("reference_images") or [], 1):
                zip_media(zf, url, f"{product}/原始母版/{index:03d}{output_extension(url)}")
            for item in run["outputs"]:
                if item.get("status") != "succeeded" or not item.get("url"):
                    continue
                plan = item["plan"]
                ext = output_extension(item["url"], item.get("media_kind") or "image")
                stem = f"{plan['index']:03d}_{export_name(plan.get('purpose'), '图片')}"
                media_dir = "视频结果" if item.get("media_kind") == "video" else "生成结果"
                zip_media(zf, item["url"], f"{product}/{media_dir}/{stem}{ext}")
                if item.get("media_kind") != "video":
                    zip_media(zf, item["url"], f"{product}/干净底图/{stem}{ext}")
                module_name = export_name(plan.get("module_name"), "详情模块")
                zip_media(zf, item["url"], f"{product}/详情页模块/{plan['index']:03d}_{module_name}/{stem}{ext}")
        return FileResponse(target, media_type="application/zip", filename=f"{product}-画布Agent交付包.zip")

    # A restart never silently resubmits paid work.
    for path in run_dir.glob("*.json"):
        run = read(path, {})
        if run and run.get("status") not in RUN_DONE:
            interrupted = 0
            for item in run.get("outputs") or []:
                if item.get("status") in {"queued", "running", "retrying"}:
                    item.update({
                        "status": "interrupted",
                        "error": "服务重启前任务已提交，未自动重发以避免重复扣费",
                    })
                    interrupted += 1
            run.update({"status": "paused", "pause_requested": True,
                        "current_stage": (
                            f"服务重启后已安全暂停，{interrupted} 张已提交图片需要确认后重试"
                            if interrupted else "服务重启后已安全暂停，请手动继续"
                        )})
            atomic(path, run)
    return {"root": str(root), "workers": workers, "parse_quantity": parse_quantity}
