import hashlib, json, logging, tempfile, threading, uuid, re
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
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


app = FastAPI(title="亲安 · 多模态反诈核验", version="3.0.0", lifespan=lifespan)
pool = ThreadPoolExecutor(max_workers=1)
jobs = {}
joblock = threading.Lock()


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
    if name not in {'known-real','known-fake','known-real-2','known-fake-2','known-real-3','known-fake-3'}:raise HTTPException(404,'公开视频不存在')
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
    return {
        "version": app.version,
        "models": models,
        "scope": "研究辅助核验，不确认身份，不保证真实性",
        "demo_video": all((ROOT/'data/demo'/f'{n}.mp4').exists() for n in ('known-real','known-fake')),
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
    return RedirectResponse('/#evidence') if (ROOT/'frontend-next/index.html').exists() else FileResponse(ROOT/'frontend/model-lab.html')


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
    try:
        suffix = path.suffix
        if suffix in {".mp4", ".mov", ".avi", ".webm"}:
            with joblock:
                jobs[key]["message"] = "正在分析视频画面"
            duration, frames = sample_video(path, 16)
            images = [im for _, im in frames]
            while len(images) < 16:
                images.append(images[-1])
            try:
                from .video_fusion import configured as fusion_configured,predict as fusion_predict
                from .gend import configured as gend_configured,predict as gend_predict
                from .ordered_video import configured as ordered_configured,predict as ordered_predict
                from .sifta import configured as sifta_configured,predict as sifta_predict
                result["modules"]["video"] = ordered_predict(path) if ordered_configured() else gend_predict(path) if gend_configured() else fusion_predict(path) if fusion_configured() else sifta_predict(path) if sifta_configured() else detector.classify("video", images)
            except Exception as e:
                logging.exception("video")
                result["modules"]["video"] = {"status": "failed", "note": str(e)}
            result["duration"] = duration
            result["sample_times"] = [t for t, _ in frames]
            if result['modules']['video'].get('moments'):
                result['sample_times']=[m['start'] for m in result['modules']['video']['moments']]
            result["limitations"].append(
                "画面分别采用16帧和4组8帧人脸片段核验，可能漏掉短暂伪造；测试仅覆盖指定来源和换脸方法，不代表所有生成视频。" if fusion_configured() else "画面采样进行人脸操纵核验，可能漏掉短暂伪造；不代表所有生成视频。"
            )
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
                jobs[key]["message"] = "正在提取并分析声音"
            try:
                samples = detector.audio_samples(path, folder)
                result["transcript"] = {"status":"disabled","text":"","note":"语音仅做声学合成检测；文字分析请使用聊天截图入口。"}
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
                result["modules"]["audio"] = {"status": "failed", "note": str(e)}
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
        if scene == "chat":result["summary"] = "聊天截图已提取，请核对内容并独立核实"
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
