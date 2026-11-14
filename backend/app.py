import hashlib, json, logging, tempfile, threading, uuid, re, time
import torch
torch.set_num_threads(2)
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from PIL import Image
from bootstrap import ROOT
from . import detector, storage
from .media import sample_video


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
    count = cleanup_interrupted()
    logging.info("Cleaned %s interrupted upload directories", count)
    from .news import start_updates
    news_stop=threading.Event()
    start_updates(news_stop)
    yield
    news_stop.set()


app = FastAPI(title="TruthLens 真鉴 · 多模态核验与反诈问答", version="3.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware,minimum_size=1000,compresslevel=6)

@app.middleware('http')
async def response_policy(request,call_next):
    response=await call_next(request)
    path=request.url.path
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    if path.startswith(('/api/cases','/api/jobs')):response.headers['Cache-Control']='no-store'
    elif path.startswith('/assets/'):response.headers['Cache-Control']='public, max-age=31536000, immutable'
    elif path=='/' or path.endswith('.html'):response.headers['Cache-Control']='no-cache'
    return response

from .agent_api import router as agent_router
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
    from .product import available as product_available

    models = {
        k: detector.available(k) for k in ("video", "audio", "image")
    }
    models["tamper"] = False
    models["product"] = product_available()
    from .chat_ocr import available as ocr_available
    models['chat_ocr'] = ocr_available()
    from .advisor import available as advisor_available
    models['advisor'] = advisor_available()
    models['speech_text'] = any(detector.available(k) for k in ('asr_zh','asr_small','asr')) and (ROOT/'models/active-chat.json').exists()
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
    if result.get('scene')!='chat':raise HTTPException(409,'这个入口只用于聊天截图，不能修改声音检测')
    from .chat_analysis import analyze as analyze_chat
    result['ocr']['text']=text
    try:result['chat_analysis']=analyze_chat(text)
    except Exception:
        logging.exception('Corrected chat interpretation')
        result['chat_analysis']={'status':'unavailable','signals':[],'note':'自动分析暂不可用，请人工核对。'}
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
    if analysis.get('assessment',{}).get('level') in {'alert','attention'}:result['summary']='校正文字中发现需核实的要求，请查看分项结果'
    else:
        signals=[]
        for module in result.get('modules',{}).values():
            if module.get('status')!='completed':continue
            if module.get('score') is not None:signals.append(module['score']>=module.get('threshold',.5))
            signals.extend(p['score']>=p.get('threshold',.5) for p in module.get('segments',[]))
        result['summary']='发现合成线索，请先核实' if any(signals) else '已重查说话内容，仍需独立核实'
    if not storage.update(result):raise HTTPException(404,'记录已删除')
    with joblock:
        if key in jobs:jobs[key]['result']=result
    return result


@app.get("/api/cases")
def cases():
    return storage.listing()


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
def get_case(key: str):
    item = storage.get(key)
    if not item:
        raise HTTPException(404, "记录不存在")
    return item


@app.delete("/api/cases/{key}")
def delete_case(key: str):
    with joblock:
        if key in jobs and jobs[key]['status']=='processing':raise HTTPException(409,'核验仍在处理，请完成后再删除报告')
        from .agent_store import delete as delete_agent_data
        delete_agent_data(key)
        storage.delete(key)
        jobs.pop(key,None)
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
        return dict(jobs[key])


def prune_jobs():
    # Called with joblock held; reports remain in SQLite after memory eviction.
    terminal=[key for key,value in jobs.items() if value['status']!='processing']
    for key in terminal[:-100]:del jobs[key]


def process(key, path, name, context, sha, folder, scene="general"):
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
        if suffix in {".mp4", ".mov", ".avi", ".webm"}:
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
                from .modern_voice import configured as acoustic_configured,predict as acoustic_predict
                if acoustic_configured():
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
        if scene == "chat":
            from .chat_ocr import read as read_chat
            from .chat_analysis import analyze as analyze_chat
            with Image.open(path) as im:
                if im.width*im.height>25_000_000:raise ValueError('截图过大，请裁剪聊天内容后重试')
                result["ocr"] = read_chat(im)
            try:result["chat_analysis"] = analyze_chat(result["ocr"]["text"])
            except Exception:
                logging.exception("screenshot interpretation")
                result["chat_analysis"] = {"status":"unavailable","signals":[],"note":"文字已提取，自动分析暂不可用，请先核对文字。"}
        if scene != "chat" and suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            with Image.open(path) as im:
                if im.width * im.height > 25_000_000:
                    raise ValueError("图片过大")
                try:
                    if scene == "product":
                        from .product import predict as product_predict
                        result["modules"]["image"] = product_predict(im.convert("RGB"))
                    else:
                        result["modules"]["image"] = detector.classify("image", [im.convert("RGB")])
                except Exception as e:
                    result["modules"]["image"] = {
                        "status": "unavailable",
                        "note": str(e),
                    }
            result["modules"]["tamper"] = {"status":"disabled","note":"局部修图定位未通过本地有效性复核，暂不提供。"}
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
        result["summary"] = (
            ("发现合成线索，请先核实" if any(tendencies) else "这次检查，还不能确认真假")
            if successes
            else "检测未成功，当前无法判断；仍可使用可信回拨"
        )
        if suffix in {".png", ".jpg", ".jpeg", ".webp"} and successes:
            result["limitations"].append(
                "图像提示依据该模型已登记的阈值；不是诈骗或真实性概率，局部改图仍可能漏检。"
            )
        if result.get('speech_analysis',{}).get('assessment',{}).get('level') in {'alert','attention'}:result['summary']='发现需核实的说话内容，请先暂停操作'+('；另有合成线索' if any(tendencies) else '')
        if scene == "chat":result["summary"] = result.get('chat_analysis',{}).get('assessment',{}).get('title','聊天截图已提取，请核对内容并独立核实')
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
                storage.save(result)
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


@app.post("/api/analyze", status_code=202)
def analyze(file: UploadFile = File(...), context: str = Form(""), scene: str = Form("general")):
    if scene not in {"general","product","chat"}:raise HTTPException(422,"未知的检测场景")
    if scene == "product":
        from .product import available as product_available
        if not product_available():raise HTTPException(503,"商品场景模型尚未通过发布检查，请使用通用核验")
    suffix = Path(file.filename or "").suffix.lower()
    if scene in {'product','chat'} and suffix not in {'.png','.jpg','.jpeg','.webp'}:
        raise HTTPException(422,'该入口只支持图片')
    if suffix not in {
        ".mp4",
        ".mov",
        ".avi",
        ".webm",
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }:
        raise HTTPException(415, "不支持的文件格式")
    if len(context) > 4000:
        raise HTTPException(422, "描述过长")
    with joblock:
        if sum(j["status"] == "processing" for j in jobs.values()) >= 3:
            raise HTTPException(429, "已有任务处理中，请稍后")
    folder = Path(tempfile.mkdtemp(dir=storage.ROOT, prefix="upload-"))
    path = folder / ("input" + suffix)
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    raise HTTPException(413, "文件超过100MB")
                digest.update(chunk)
                out.write(chunk)
        if not size:
            raise HTTPException(422, "文件为空")
    except Exception:
        import shutil

        shutil.rmtree(folder)
        raise
    finally:
        file.file.close()
    key = uuid.uuid4().hex
    with joblock:
        jobs[key] = {"status": "processing", "message": "已提交，等待检测"}
    pool.submit(
        process,
        key,
        path,
        Path(file.filename).name,
        context,
        digest.hexdigest(),
        folder,
        scene,
    )
    return {"job_id": key}


app.mount("/", StaticFiles(directory=ROOT / ('frontend-next' if (ROOT/'frontend-next/index.html').exists() else 'frontend'), html=True), name="web")
