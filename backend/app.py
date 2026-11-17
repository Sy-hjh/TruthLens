import hashlib, ipaddress, json, logging, os, stat, tempfile, threading, uuid, re, time
import torch
torch.set_num_threads(2)
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
from bootstrap import ROOT
from . import detector, storage
from .companion import ANSWER_LIMIT
from .fraud_risk import has_fraud_language, is_fraud_task
from .report_summary import update_summary
from .media import sample_video
from . import admin_store
from .admin_api import current_account, require_account, router as admin_router


def cleanup_interrupted():
    import shutil

    root = storage.ROOT.resolve()
    removed = 0
    for directory in root.glob("upload-*"):
        if (
            re.fullmatch(r"upload-[a-z0-9_]{8}", directory.name)
            and not directory.is_symlink()
            and directory.is_dir()
            and directory.resolve().parent == root
        ):
            shutil.rmtree(directory)
            removed += 1
    return removed


@asynccontextmanager
async def lifespan(_app):
    storage.initialize()
    admin_store.initialize()
    admin_store.ensure_setup_token()
    count = cleanup_interrupted()
    logging.info("Cleaned %s interrupted upload directories", count)
    from .news import start_updates
    news_stop=threading.Event()
    start_updates(news_stop)
    threading.Thread(target=run_retention, args=(news_stop,), daemon=True, name="report-retention").start()
    yield
    news_stop.set()


app = FastAPI(title="真鉴 · AI 内容核验助手", version="3.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware,minimum_size=1000,compresslevel=6)


def report_access(account, key, *, running=False):
    if account["role"] == "admin":
        return True
    if running:
        with joblock:
            if key in jobs:
                return jobs[key].get("owner_id") == account["id"]
    return storage.owned_by(key, account["id"])


def authorize(request):
    path = request.url.path
    if path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.url.netloc}"
        if (origin and origin != expected) or request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "请在真鉴页面中完成此操作。")
    if path == "/api/agent/metrics":
        require_account(request, admin=True)
    if (path in {"/api/analyze", "/api/cases"} or
            path.startswith(("/api/cases/", "/api/jobs/", "/api/companion/")) and path != "/api/companion/model"):
        account = require_account(request)
        if path.startswith(("/api/cases/", "/api/jobs/")):
            key = path.split("/")[3]
            if not report_access(account, key, running=path.startswith("/api/jobs/")):
                raise HTTPException(404, "没有这份核验记录。")


@app.middleware('http')
async def response_policy(request,call_next):
    try:
        await run_in_threadpool(authorize, request)
    except HTTPException as error:
        response = JSONResponse({"detail":error.detail}, status_code=error.status_code)
    else:
        response = await call_next(request)
    path=request.url.path
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    if path.startswith(('/api/cases','/api/jobs','/api/companion','/api/auth','/api/admin','/api/verification-cases')):response.headers['Cache-Control']='no-store'
    elif path.startswith('/assets/'):response.headers['Cache-Control']='public, max-age=31536000, immutable'
    elif path=='/' or path.endswith('.html'):response.headers['Cache-Control']='no-cache'
    return response

from .agent_api import router as agent_router
app.include_router(admin_router)
app.include_router(agent_router)
pool = ThreadPoolExecutor(max_workers=1)
asr_pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix="qinan-asr")

def timed_transcription(samples):
    start=time.monotonic()
    try:result=detector.transcribe(samples)
    except Exception:
        logging.exception("Independent transcription failed")
        result={"status":"unavailable","text":"","note":"转写模型运行失败，不代表没有音轨。"}
    return result,time.monotonic()-start

jobs = {}
joblock = threading.Lock()

def video_predictor():
    """Import only the configured detector; never initialize unused model stacks."""
    from importlib import import_module
    config=ROOT/'models/active-video.json'
    engine=json.loads(config.read_text(encoding='utf-8')).get('engine') if config.exists() else None
    modules={'video-ordered-head':'.ordered_video','gend-clip':'.gend','video-fusion':'.video_fusion','sifta':'.sifta'}
    if engine not in modules:return None,False
    module=import_module(modules[engine],package=__package__)
    return (module.predict,engine=='video-fusion') if module.configured() else (None,False)


@app.get("/api/demo/{name}")
def demo(name: str):
    if name not in {
        "family-simulation",
        "expert-simulation",
        "normal-synthetic-control",
        "guidance-contact-family",
        "guidance-edited-image",
        "guidance-ai-image",
        "guidance-inconclusive",
    }:
        raise HTTPException(404, "模拟材料不存在")
    path = ROOT / "data/demo" / (name + ".mp3")
    if not path.exists():
        raise HTTPException(404, "模拟材料尚未生成")
    return FileResponse(path, media_type="audio/mpeg", filename=name + ".mp3")


Image.MAX_IMAGE_PIXELS = 25_000_000


@app.get('/api/demo-video/{name}')
def demo_video(name: str):
    if name not in {'known-real','known-fake','known-real-2','known-fake-2','known-real-3','known-fake-3','av-real','av-fake'}:raise HTTPException(404,'公开视频不存在')
    path=ROOT/'data/demo'/f'{name}.mp4'
    if not path.exists():raise HTTPException(404,'公开视频尚未准备')
    return FileResponse(path,media_type='video/mp4',filename=path.name)
RULES = {
    "紧急转账": ["转账", "汇款", "手术费", "保证金", "安全账户"],
    "阻止独立核实": ["不要告诉", "别告诉", "保密", "不要打电话"],
    "高收益承诺": ["稳赚", "保本", "翻倍", "百分之百"],
    "冒用权威": ["公安", "警察", "专家", "医生"],
}


def phrase_evidence(text):
    from opencc import OpenCC

    text = OpenCC("t2s").convert(text)
    evidence = []
    for name, words in RULES.items():
        for word in words:
            for match in re.finditer(re.escape(word), text):
                prefix = text[max(0, match.start() - 8) : match.start()]
                if name == "紧急转账" and re.search(
                    r"(不涉及|不需要|不要|暂停|禁止|切勿|无需).{0,4}$", prefix
                ):
                    continue
                evidence.append(
                    {
                        "category": name,
                        "excerpt": word,
                        "context": text[
                            max(0, match.start() - 12) : min(
                                len(text), match.end() + 18
                            )
                        ],
                        "note": "规范化文字中的规则命中，只是核实线索，不能单独认定诈骗",
                    }
                )
                break
    return evidence


@app.get("/api/health")
def health():
    from .daf_image import available as daf_available
    from .product import available as product_available
    from .fused_image import available as tamper_available

    models = {
        k: detector.available(k) for k in ("video", "audio", "image")
    }
    models["tamper"] = tamper_available()
    models["daf"] = daf_available()
    models["product"] = product_available()
    from .chat_ocr import available as ocr_available
    models['chat_ocr'] = ocr_available()
    from .advisor import available as advisor_available
    models['advisor'] = advisor_available()
    models['speech_text'] = any(detector.available(k) for k in ('asr_zh','asr_small','asr')) and ((ROOT/'models/active-chat.json').exists() or models['advisor'])
    return {
        "version": app.version,
        "models": models,
        "scope": "研究辅助核验，不确认身份，不保证真实性",
        "demo_video": all((ROOT/'data/demo'/f'{n}.mp4').exists() for n in ('known-real','known-fake')),
        "demo_av": all((ROOT/'data/demo'/f'{n}.mp4').exists() for n in ('av-real','av-fake')),
    }


@app.post('/api/cases/{key}/chat-text')
def correct_chat_text(key:str,text:str=Form(...)):
    if not text.strip() or len(text)>4000:raise HTTPException(422,'请填写1到4000字的截图文字')
    result=storage.get(key)
    if not result:raise HTTPException(404,'记录不存在')
    if 'ocr' not in result:raise HTTPException(409,'此入口仅用于校正图片识别的文字')
    from .chat_analysis import analyze as analyze_chat
    result['ocr']['text']=text
    try:result['chat_analysis']=analyze_chat(text)
    except Exception:
        logging.exception('Corrected chat interpretation')
        result['chat_analysis']={'status':'unavailable','signals':[],'note':'自动分析暂不可用，请人工核对。'}
    update_summary(result)
    if not storage.update(result):raise HTTPException(404,'记录已删除')
    with joblock:
        if key in jobs:jobs[key]['result']=result
    return result


@app.post('/api/cases/{key}/speech-text')
def correct_speech_text(key:str,text:str=Form(...)):
    if not text.strip() or len(text)>4000:raise HTTPException(422,'请填写1到4000字的转写文字')
    result=storage.get(key)
    if not result:raise HTTPException(404,'记录不存在')
    if result.get('scene')=='chat' or 'transcript' not in result:raise HTTPException(409,'此入口仅用于音视频转写校正')
    from .speech_content import analyze_text
    analysis=analyze_text(text)
    previous=result.get('transcript',{})
    result['transcript']=dict(previous,text=text,original_text=previous.get('original_text',previous.get('text','')),corrected=True)
    result['speech_analysis']=analysis
    result['speech_analysis']['input_basis']='user_corrected_transcript'
    update_summary(result)
    if not storage.update(result):raise HTTPException(404,'记录已删除')
    with joblock:
        if key in jobs:jobs[key]['result']=result
    return result


@app.get("/api/cases")
def cases(request: Request):
    account = require_account(request)
    rows = storage.listing(owner_id=None if account["role"] == "admin" else account["id"])
    for row in rows:
        row.pop("marked_jpeg", None)
        row.get("modules", {}).get("tamper", {}).pop("marked_jpeg", None)
    return rows


@app.get('/api/evidence')
def evidence():
    from .evidence import summary
    return summary()


@app.get('/api/news')
def recent_news(refresh: bool=False):
    from .news import get_news
    return get_news(refresh)


class AdviceRequest(BaseModel):
    question: str = Field(default='我现在应该怎么独立核实？',min_length=1,max_length=200)


class CompanionTurn(BaseModel):
    question: str = Field(min_length=1,max_length=320)
    answer: str = Field(min_length=1,max_length=ANSWER_LIMIT)


class CompanionRequest(BaseModel):
    question: str = Field(min_length=1,max_length=320)
    page: str = Field(default='home',pattern='^(home|check|contacts|practice|history|report)$')
    history: list[CompanionTurn] = Field(default_factory=list,max_length=5)
    report_id: str | None = Field(default=None, min_length=1, max_length=80)


@app.get('/api/companion/model')
def companion_model():
    from .companion_online import OnlineModelError, configured_model
    try:
        online = configured_model()
    except OnlineModelError as exc:
        return {'mode': 'configuration_error', 'message': str(exc)}
    return {'mode': 'online' if online else 'local'}


@app.post('/api/companion/ask')
def companion_ask(body: CompanionRequest, request: Request):
    from .agent_api import _slots
    from .companion import answer, selected_attachment
    question = body.question.strip()
    if not question:raise HTTPException(422,'请输入问题')
    if body.report_id and not report_access(require_account(request), body.report_id):
        raise HTTPException(404,'报告不存在，请重新选择材料核验。')
    if not body.report_id:
        attachment = selected_attachment(question)
        if attachment:
            return attachment
    if not _slots.acquire(blocking=False):raise HTTPException(429,'助手正在处理另一份提问，请稍后重试')
    try:
        report = storage.get(body.report_id) if body.report_id else None
        if body.report_id and not report:raise HTTPException(404,'报告不存在，请重新选择材料核验。')
        return answer(question,body.page,[turn.model_dump() for turn in body.history],report=report)
    finally:_slots.release()


@app.post('/api/companion/transcribe')
def companion_transcribe(file: UploadFile = File(...)):
    if not any(detector.available(kind) for kind in ('asr_zh','asr','asr_small')):
        raise HTTPException(503,'语音转写暂不可用，请打字输入。')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.webm','.ogg','.m4a'}:
        raise HTTPException(415,'无法读取这种录音格式，请打字输入。')
    content = file.file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(422,'录音为空或过长，请重新录制。')
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ('question' + suffix)
            path.write_bytes(content)
            result = detector.transcribe(detector.audio_samples(path, folder))
    except Exception:
        logging.exception('Companion transcription failed')
        raise HTTPException(422,'录音无法转写，请重录或打字输入。')
    transcript = result.get('text','').strip()
    if not transcript:
        raise HTTPException(422,'没有识别到清晰的文字，请重录或打字输入。')
    return {'text': transcript[:320]}


@app.post('/api/cases/{key}/advice')
def advice(key: str, body: AdviceRequest):
    result=storage.get(key)
    if not result:raise HTTPException(404,'报告不存在')
    from .advisor import explain
    return explain(result,body.question)


@app.get('/model-lab.html')
def model_lab_redirect():
    return RedirectResponse('/#home') if (ROOT/'frontend-next/index.html').exists() else FileResponse(ROOT/'frontend/model-lab.html')


@app.get("/api/cases/{key}")
def get_case(key: str, request: Request):
    item = storage.get(key)
    if not item:
        raise HTTPException(404, "记录不存在")
    admin_store.audit(current_account(request), "查看核验报告", key)
    return item


@app.get("/api/cases/{key}/pdf")
def export_case_pdf(key: str, request: Request):
    item = storage.get(key)
    if not item:
        raise HTTPException(404, "记录不存在")
    from .report_pdf import build_report_pdf

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", key)[:80]
    admin_store.audit(current_account(request), "导出报告 PDF", key)
    return Response(build_report_pdf(item), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="TruthLens-{safe_id}.pdf"',
        "Cache-Control": "no-store",
    })


@app.delete("/api/cases/{key}")
def delete_case(key: str, request: Request):
    with joblock:
        if key in jobs and jobs[key]['status']=='processing':raise HTTPException(409,'核验仍在处理，请完成后再删除报告')
        from .agent_store import delete as delete_agent_data
        delete_agent_data(key)
        storage.delete(key)
        jobs.pop(key,None)
    admin_store.audit(current_account(request), "删除核验报告", key)
    return {"deleted": True}


@app.post("/api/cases/{key}/transcript")
def correct_transcript(key: str, text: str = Form(...)):
    raise HTTPException(410, "语音转写分析入口已关闭；文字分析请上传聊天截图。")


@app.get("/api/jobs/{key}")
def job(key: str):
    with joblock:
        if key not in jobs:
            saved=storage.get(key)
            if saved:return dict(status='completed',message='已从保存的报告恢复',result=saved)
            raise HTTPException(404, "任务不存在；若服务中途重启，请重新提交材料")
        return {field: value for field, value in jobs[key].items() if field != "owner_id"}


def prune_jobs():
    # Called with joblock held; reports remain in SQLite after memory eviction.
    terminal=[key for key,value in jobs.items() if value['status']!='processing']
    for key in terminal[:-100]:del jobs[key]


def run_retention(stop):
    from .agent_store import delete as delete_agent_data

    while not stop.is_set():
        try:
            days = admin_store.active_settings()["values"]["retention_days"]
            if days:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                expired = storage.expired_reports(cutoff)
                for key in expired:
                    with joblock:
                        delete_agent_data(key)
                        storage.delete(key)
                        jobs.pop(key, None)
                if expired:
                    admin_store.audit(None, "清理到期报告", f"{len(expired)} 份")
        except Exception:
            logging.exception("Report retention sweep")
        stop.wait(1800)


def check_image_text(result, image, *, auto=False):
    from .chat_analysis import analyze as analyze_chat
    from .chat_ocr import NoReadableText, read as read_chat
    from .image_fields import document_kind

    try:
        ocr = read_chat(ImageOps.exif_transpose(image))
    except NoReadableText:
        if not auto:
            result["chat_analysis"] = {"status": "unavailable", "signals": [], "note": "没有读到清晰文字。"}
        return {}
    except Exception:
        logging.exception("image text recognition")
        if not auto:
            result["chat_analysis"] = {"status": "unavailable", "signals": [], "note": "未完成文字识别。"}
        return {"status": "unavailable"}
    try:
        analysis = analyze_chat(ocr["text"])
    except Exception:
        logging.exception("image text interpretation")
        analysis = {"status": "unavailable", "signals": [], "note": "文字已提取，可核对原话。"}
    if not auto or document_kind(ocr["lines"]) == "image" or has_fraud_language(analysis):
        result["ocr"] = ocr
        result["chat_analysis"] = analysis
    return ocr


def check_image_models(result, path, image, *, ocr=None, reference_path=None, settings=None):
    from .chat_ocr import NoReadableText, read
    from .daf_image import predict as predict_daf
    from .fused_image import METHOD, available as tamper_available, marked_preview, predict as predict_tamper
    from .image_fields import task_fields, visible_generation_label
    from .image_marks import MARK_POLICY, report_regions

    modules = result["modules"]
    config = settings["values"] if settings else {}
    try:
        if result["scene"] == "product":
            from .product import predict as product_predict
            modules["image"] = product_predict(image.convert("RGB"))
        else:
            modules["image"] = detector.classify("image", [image.convert("RGB")])
    except Exception as exc:
        modules["image"] = {"status": "unavailable", "note": str(exc)}
    if config and modules["image"]["status"] == "completed":
        modules["image"].update(threshold=config["whole_threshold"], weight=config["whole_weight"])
    oriented = ImageOps.exif_transpose(image)
    if ocr is None:
        try:
            ocr = read(oriented)
        except NoReadableText:
            ocr = {}
        except Exception:
            logging.exception("Read image field positions")
            ocr = {"status": "unavailable"}
    context = result.get("context", "")
    lines = ocr.get("lines", [])
    fields = task_fields(lines, oriented.size, context)
    generation_label = visible_generation_label(lines, oriented.size)
    if generation_label:
        modules["image"]["generation_label"] = generation_label
    modules["tamper"] = {"status": "unavailable", "method": METHOD, "note": "图片异常检查未完成。"}
    if tamper_available():
        try:
            modules["tamper"] = predict_tamper(path, image, context=context, ocr=ocr,
                                               mask_threshold=config.get("fused_threshold", 0.5),
                                               photo_threshold=config.get("fused_photo_threshold", 0.75))
        except Exception:
            logging.exception("FUSED image inspection")
    if fields:
        try:
            modules["daf"] = predict_daf(path, fields, threshold=config.get("daf_signal_threshold", 0.4))
            focus = task_fields(lines, oriented.size, context, explicit_only=True)
            if focus:
                modules["daf"]["focus_fields"] = list(dict.fromkeys(field for _, field in focus))
        except Exception:
            logging.exception("DAF text edit inspection")
            modules["daf"] = {"status": "unavailable", "method": "daf", "note": "文字编辑检查未完成。"}
    if config:
        modules["image"]["weight"] = config["whole_weight"]
        modules["tamper"]["weight"] = config["fused_weight"]
        if "daf" in modules:
            modules["daf"].update(weight=config["daf_weight"], review_threshold=config["daf_box_threshold"])
        result["detection_config_version"] = settings["version"]
    if reference_path:
        from .image_comparison import compare_fields

        try:
            with Image.open(reference_path) as source:
                if source.width * source.height > 25_000_000:
                    raise ValueError("参考图片过大")
                reference = ImageOps.exif_transpose(source)
                modules["reference"] = compare_fields(oriented, reference, read(reference)["lines"], context)
        except (NoReadableText, OSError, ValueError):
            modules["reference"] = {"status": "unavailable", "note": "参考图无法读取或没有可比对的关键文字。", "regions": []}
        except Exception:
            logging.exception("Reference image comparison")
            modules["reference"] = {"status": "unavailable", "note": "参考图比对未完成。", "regions": []}

    from .image_risk import assess_image
    from .risk_labels import PRIORITY_REVIEW, REVIEW

    regions = report_regions(modules)
    if regions and assess_image(modules)["title"] in {REVIEW, PRIORITY_REVIEW}:
        result["marked_jpeg"] = marked_preview(oriented, regions)
        result["mark_policy"] = MARK_POLICY


def process(key, path, name, context, sha, folder, scene="general", audio_only=False, reference_path=None,
            owner_id=None, settings=None):
    result = {
        "id": key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": name,
        "scene": scene,
        "context": context,
        "internal_only": context.startswith('__truthlens_qa__'),
        "sha256": sha,
        "modules": {},
        "phrases": [],
        "limitations": [
            "未确认视频中的人物身份；即使没有发现异常，也应通过预留号码核实。",
            "画面与声音分别检测，尚未实现音画同步鉴定。",
            "AI生成、编辑与诈骗意图不能画等号。",
        ],
        "next_steps": [
            "先不要转账，也不要提供验证码。",
            "通过您提前保存的家人常用号码回拨核实。",
            "保留原始聊天与转账记录，必要时寻求线下帮助。",
        ],
    }
    finished = False
    started=time.monotonic();result['timings']={};samples=None;decode_error=None;asr_future=None
    try:
        from .resource_budget import prepare as prepare_resources
        result['resource_policy']=prepare_resources()
        suffix = path.suffix
        if suffix in {'.mp4','.mov','.avi','.webm','.wav','.mp3','.m4a','.flac','.ogg'}:
            step=time.monotonic()
            with joblock:jobs[key]['message']='正在读取音轨（随后分开检查画面、声音和内容）'
            try:
                samples=detector.audio_samples(path,folder)
                result['audio_info']={'status':'available','sample_rate':16000,'seconds':len(samples)/16000}
                asr_future=asr_pool.submit(timed_transcription,samples)
            except Exception as exc:
                decode_error=exc;result['audio_info']={'status':'unavailable','code':getattr(exc,'code','decode_failed'),'note':str(exc)}
            result['timings']['audio_decode_seconds']=time.monotonic()-step
        video_started=time.monotonic()
        if not audio_only and suffix in {".mp4", ".mov", ".avi", ".webm"}:
            with joblock:
                jobs[key]["message"] = "正在分析视频画面"
            duration=0.;frames=[];fusion_active=False
            try:
                predict_video,fusion_active=video_predictor()
                if predict_video:
                    import cv2
                    cap=cv2.VideoCapture(str(path))
                    try:
                        fps=cap.get(cv2.CAP_PROP_FPS);duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps if fps>0 else 0.
                    finally:cap.release()
                    images=[]
                else:
                    duration,frames=sample_video(path,16);images=[im for _,im in frames]
                    while len(images)<16:images.append(images[-1])
                result["modules"]["video"] = predict_video(path) if predict_video else detector.classify("video", images)
            except Exception as e:
                logging.exception("video")
                result["modules"]["video"] = {"status": "failed", "note": str(e)}
            result["duration"] = duration
            result["sample_times"] = [t for t, _ in frames]
            if result['modules']['video'].get('moments'):
                result['sample_times']=[m['start'] for m in result['modules']['video']['moments']]
            result["limitations"].append(
                "画面分别采用16帧和4组8帧人脸片段核验，可能漏掉短暂伪造；测试仅覆盖指定来源和换脸方法，不代表所有生成视频。" if fusion_active else "画面采样进行人脸操纵核验，可能漏掉短暂伪造；不代表所有生成视频。"
            )
        result['timings']['video_seconds']=time.monotonic()-video_started
        if suffix in {
            ".mp4",
            ".mov",
            ".avi",
            ".webm",
            ".wav",
            ".mp3",
            ".m4a",
            ".flac",
            ".ogg",
        }:
            with joblock:
                jobs[key]["message"] = "音轨已读取，正在检测合成声音（转写同步进行）" if samples is not None else "正在核对音轨读取结果"
            acoustic_started=time.monotonic()
            try:
                if samples is None:raise decode_error or ValueError('未读取到音轨')
                from .ast_voice import configured as ast_configured, predict as ast_predict
                from .modern_voice import configured as acoustic_configured,predict as acoustic_predict
                if ast_configured():
                    result['modules']['audio'] = ast_predict(samples)
                elif acoustic_configured():
                    result["modules"]["audio"] = acoustic_predict(samples)
                else:
                    segments = []
                    from .voice_forensics import available as modern_voice_available
                    window=80000 if modern_voice_available() else 160000
                    for start in range(0, len(samples), window):
                        chunk = samples[start : start + window]
                        if len(chunk) >= 16000:
                            item = detector.classify("audio", chunk)
                            item.update(
                                start=start / 16000,
                                end=(start+len(chunk))/16000,
                                signal=(
                                    "较强合成线索，仍需核实"
                                    if item["score"] >= item.get('threshold',0.5)
                                    else (
                                        "未检出明显合成线索，不代表身份真实"
                                        if item["score"] <= 0.2
                                        else "结果不明确，暂不作判断"
                                    )
                                ),
                            )
                            segments.append(item)
                    result["modules"]["audio"] = {
                        "status": "completed",
                        "analysis_basis":"acoustic_waveform_only",
                        "sample_rate":16000,
                        "analyzed_seconds":len(samples)/16000,
                        "segments": segments,
                        "source": segments[0].get('source') if segments else None,
                        "note": f"直接分析16kHz声音波形，按{window//16000}秒切片；不调用语音转写，不依据说话内容判断AI声音。",
                    }
                result["limitations"].append(
                    "AST 声音检测分析开头最多 4 秒；目前的适配评测集中在千问仿声样本。" if ast_configured() else
                    ("当前声音版本以真实/参考克隆语音及压缩条件评测，不确认人物身份，不保证覆盖所有新型克隆方法。" if acoustic_configured() else "旧声音版本只做过通用TTS对照，不能代表真人克隆检测能力。")
                )
            except Exception as e:
                logging.exception("audio")
                result["modules"]["audio"] = {"status": "failed", "note": str(e),"failure_stage":"model" if samples is not None else "decode","failure_code":getattr(e,"code","model_failed" if samples is not None else "decode_failed")}
            result['timings']['acoustic_seconds']=time.monotonic()-acoustic_started
            if samples is not None:
                with joblock:jobs[key]['message']='正在转写声音并检查内容风险'
                from .speech_content import check as check_speech_content
                transcript,asr_seconds=asr_future.result()
                result['timings']['asr_seconds']=asr_seconds
                content_started=time.monotonic()
                result['transcript'],result['speech_analysis']=check_speech_content(samples,transcript=transcript)
                result['timings']['content_seconds']=time.monotonic()-content_started
            else:
                result['transcript']={'status':'unavailable','text':'','note':str(decode_error or '未取得可读取的音轨。')}
                result['speech_analysis']={'status':'unavailable','signals':[],'note':'没有可用声音，未分析内容。'}
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            fraud_task = is_fraud_task(context)
            with Image.open(path) as im:
                if im.width * im.height > 25_000_000:
                    raise ValueError("图片过大")
                ocr = None
                if scene in {"chat", "auto", "general"} or fraud_task:
                    with joblock:jobs[key]['message']='正在识别并检查文字'
                    ocr = check_image_text(result, im, auto=scene != "chat" and not fraud_task)
                if scene != "chat" or reference_path or fraud_task or has_fraud_language(result.get("chat_analysis", {})):
                    with joblock:jobs[key]['message']='正在检查图片异常'
                    check_image_models(result, path, im, ocr=ocr, reference_path=reference_path, settings=settings)
        successes = [
            m for m in result["modules"].values() if m["status"] == "completed"
        ]
        tendencies = []
        for module in successes:
            if "score" in module:
                tendencies.append(module["score"] >= module.get('threshold',0.5))
            tendencies.extend(s["score"] >= s.get('threshold',0.5) for s in module.get("segments", []))
        if len(set(tendencies)) > 1:
            result["limitations"].append(
                "不同检测项的倾向有差异：整图生成与局部编辑是不同任务，画面和声音也可能只有一项被伪造；不计算统一真伪分数。"
            )
        update_summary(result)
        result['timings']['total_seconds']=time.monotonic()-started
        finished = True
    except Exception:
        logging.exception("job")
        with joblock:
            jobs[key].update(
                status="failed", message="文件无法处理，请换用有效素材重试"
            )
    finally:
        import shutil

        try:
            shutil.rmtree(folder)
            if finished:
                storage.save(result, owner_id=owner_id)
                with joblock:
                    jobs[key].update(
                        status="completed",
                        message="报告已生成，临时材料已清理",
                        result=result,
                    )
                    prune_jobs()
        except Exception:
            logging.exception("finalization")
            with joblock:
                jobs[key].update(
                    status="failed",
                    message="结果保存或临时文件清理失败，请查看日志后重试",
                )


MEDIA_SUFFIXES = {'.mp4','.mov','.avi','.webm','.wav','.mp3','.m4a','.flac','.ogg','.jpg','.jpeg','.png','.webp'}
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def save_upload(source, path, digest=None):
    size = 0
    with path.open("wb") as out:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > 100 * 1024 * 1024:
                raise HTTPException(413, "文件超过100MB")
            if digest is not None:
                digest.update(chunk)
            out.write(chunk)
    if not size:
        raise HTTPException(422, "文件为空")


def queue_verification(source, filename: str, context: str, scene: str, audio_only: bool, reference=None, account=None):
    if scene not in {"general","auto","product","chat"}:raise HTTPException(422,"未知的检测场景")
    if scene == "product":
        from .product import available as product_available
        if not product_available():raise HTTPException(503,"商品场景模型尚未通过发布检查，请使用通用核验")
    suffix = Path(filename).suffix.lower()
    if audio_only and (scene != 'general' or suffix not in {'.webm','.ogg','.m4a'}):
        raise HTTPException(422,'录音格式不受支持')
    if scene in {'product','chat'} and suffix not in {'.png','.jpg','.jpeg','.webp'}:
        raise HTTPException(422,'该入口只支持图片')
    if suffix not in MEDIA_SUFFIXES:
        raise HTTPException(415, "不支持的文件格式")
    if reference and (suffix not in IMAGE_SUFFIXES or Path(reference.filename or '').suffix.lower() not in IMAGE_SUFFIXES):
        raise HTTPException(415, "参考图比对仅支持图片")
    if len(context) > 4000:
        raise HTTPException(422, "描述过长")
    key = uuid.uuid4().hex
    owner_id = account["id"] if account else None
    settings = admin_store.active_settings() if account and suffix in IMAGE_SUFFIXES else None
    with joblock:
        if sum(j["status"] == "processing" for j in jobs.values()) >= 3:
            raise HTTPException(429, "已有任务处理中，请稍后")
        jobs[key] = {"status": "processing", "message": "正在准备材料", "owner_id": owner_id}
    folder = None
    digest = hashlib.sha256()
    try:
        folder = Path(tempfile.mkdtemp(dir=storage.ROOT, prefix="upload-"))
        path = folder / ("input" + suffix)
        save_upload(source, path, digest)
        reference_path = None
        if reference:
            reference_path = folder / "reference"
            save_upload(reference.file, reference_path)
        with joblock:
            jobs[key]['message'] = '已提交，等待检测'
        pool.submit(process, key, path, Path(filename).name, context, digest.hexdigest(), folder, scene, audio_only,
                    reference_path, owner_id, settings)
    except Exception:
        import shutil
        with joblock:
            jobs.pop(key, None)
        if folder is not None:
            shutil.rmtree(folder)
        raise
    return {"job_id": key}


@app.post("/api/analyze", status_code=202)
def analyze(request: Request, file: UploadFile = File(...), context: str = Form(""), scene: str = Form("general"),
            audio_only: bool = Form(False), reference: UploadFile | None = File(None)):
    try:
        return queue_verification(file.file, file.filename or '', context, scene, audio_only, reference,
                                  account=require_account(request))
    finally:
        file.file.close()
        if reference:
            reference.file.close()


class LocalFileRequest(BaseModel):
    path: str | None = Field(default=None, min_length=1, max_length=1024)
    desktop_filename: str | None = Field(default=None, min_length=1, max_length=255)
    drive: str | None = Field(default=None, pattern=r'^[A-Za-z]$')
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    context: str = Field(default='', max_length=4000)


def desktop_directory():
    if os.name == 'nt':
        import ctypes

        folder = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, folder) == 0:
            return Path(folder.value)
    return Path.home() / 'Desktop'


def matching_media_names(filename):
    if not re.fullmatch(r'[^\\/:\x00-\x1f<>"|?*]+', filename) or filename in {'.', '..'} or Path(filename).is_reserved():
        raise HTTPException(422, '请提供音频、图片或视频的文件名。')
    key = filename.casefold()
    return {key} if Path(filename).suffix.lower() in MEDIA_SUFFIXES else {key + suffix for suffix in MEDIA_SUFFIXES}


def unique_file(matches, location, filename):
    if not matches:
        raise HTTPException(404, f'{location}没有找到名为「{filename}」的可读取媒体文件。请核对文件名或添加附件。')
    if len(matches) > 1:
        raise HTTPException(422, {
            'code': 'ambiguous_file',
            'message': f'{location}找到多个同名文件。请选择要核验的一份。',
            'paths': [str(item) for item in sorted(matches)[:5]],
        })
    return matches[0]


def find_desktop_file(filename, desktop):
    names = matching_media_names(filename)
    matches = [item for item in desktop.iterdir() if item.name.casefold() in names and not item.is_symlink() and item.is_file()]
    return unique_file(matches, '桌面上', filename)


def find_drive_file(filename, root, *, timeout=30):
    names = matching_media_names(filename)
    deadline = time.monotonic() + timeout

    def incomplete():
        if matches:
            raise HTTPException(408, {
                'code': 'incomplete_file_search',
                'message': '找到一个匹配文件，搜索仍有未覆盖的文件夹。确认路径后，点击即可核验。',
                'paths': [str(matches[0])],
            })
        raise HTTPException(408, '搜索超时。请发更具体的文件夹路径或添加附件。')

    pending, matches = deque([root]), []
    while pending and len(matches) < 5:
        if time.monotonic() >= deadline:
            if len(matches) > 1:
                break
            incomplete()
        try:
            with os.scandir(pending.popleft()) as entries:
                for entry in entries:
                    if time.monotonic() >= deadline:
                        if len(matches) > 1:
                            return unique_file(matches, '指定位置中', filename)
                        incomplete()
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            attrs = getattr(entry.stat(follow_symlinks=False), 'st_file_attributes', 0)
                            if not attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                                pending.append(entry.path)
                        elif entry.name.casefold() in names and entry.is_file(follow_symlinks=False):
                            matches.append(Path(entry.path))
                            if len(matches) >= 5:
                                break
                    except OSError:
                        continue
        except OSError:
            continue
    return unique_file(matches, '指定位置中', filename)


@app.post('/api/companion/local-file', status_code=202)
def companion_local_file(body: LocalFileRequest, request: Request):
    try:
        same_computer = request.client and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        same_computer = False
    own_origin = f'{request.url.scheme}://{request.url.netloc}'
    if not same_computer or request.url.hostname not in {'localhost', '127.0.0.1', '::1'} or request.headers.get('origin') != own_origin:
        raise HTTPException(403, '本机路径可在运行真鉴的电脑上使用。也可以点「添加附件」选择文件。')

    if (sum(map(bool, (body.path, body.desktop_filename, body.drive))) != 1
            or (body.drive and not body.filename) or (body.desktop_filename and body.filename)):
        raise HTTPException(422, '请提供完整路径，或告诉我文件名和它所在的桌面或盘符。')
    try:
        desktop = None
        drive_root = None
        if body.desktop_filename:
            desktop = desktop_directory().resolve(strict=True)
            candidate = find_desktop_file(body.desktop_filename.strip(), desktop)
        elif body.drive and body.filename:
            drive_root = Path(body.drive.upper() + ':\\').resolve(strict=True)
            candidate = find_drive_file(body.filename.strip(), drive_root)
        else:
            raw = (body.path or '').strip().strip('"“”')
            if not re.fullmatch(r'[a-zA-Z]:[\\/][^:\x00-\x1f<>"|?*]*', raw):
                raise HTTPException(422, '请提供盘符开头的完整文件路径，包括文件名。')
            candidate = Path(raw)
            if body.filename:
                drive_root = candidate.resolve(strict=True)
                if not drive_root.is_dir() or not re.fullmatch(r'[a-zA-Z]:', drive_root.drive):
                    raise HTTPException(422, '请提供本机磁盘上的文件夹路径。')
                candidate = find_drive_file(body.filename.strip(), drive_root)
        source_path = candidate.resolve(strict=True)
        if desktop is not None and source_path.parent != desktop:
            raise HTTPException(422, '请选择直接保存在桌面上的文件。')
        if drive_root is not None and not source_path.is_relative_to(drive_root):
            raise HTTPException(422, '请选择指定位置中的普通文件。')
        if not re.fullmatch(r'[a-zA-Z]:', source_path.drive) or candidate.is_reserved() or source_path.is_reserved():
            raise HTTPException(422, '请使用本机磁盘上的普通文件。')
        if source_path.is_dir():
            raise HTTPException(422, {'code': 'filename_required', 'message': '这个位置是文件夹。请再告诉我文件名。'})
        if candidate.suffix.lower() not in MEDIA_SUFFIXES or source_path.suffix.lower() not in MEDIA_SUFFIXES:
            raise HTTPException(415, '请选图片、视频或音频文件。')
        if not source_path.is_file():
            raise HTTPException(422, '请使用本机磁盘上的普通文件。')
        with source_path.open('rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise HTTPException(422, '请使用本机磁盘上的普通文件。')
            result = queue_verification(source, candidate.name, body.context, 'general', False,
                                        account=require_account(request))
            return {**result, 'filename': candidate.name}
    except FileNotFoundError:
        raise HTTPException(404, '没找到这个文件。请核对文件夹和文件名，也可以点「添加附件」。') from None
    except (OSError, RuntimeError):
        raise HTTPException(422, '没能读取这个文件。请检查读取权限，或点「添加附件」选择文件。') from None


app.mount("/", StaticFiles(directory=ROOT / ('frontend-next' if (ROOT/'frontend-next/index.html').exists() else 'frontend'), html=True), name="web")
