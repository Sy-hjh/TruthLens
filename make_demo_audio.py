"""Fictional, clearly labelled simulations using a generic Microsoft neural voice."""

import bootstrap, asyncio, json, hashlib
import edge_tts

SCRIPTS = {
    "family-simulation": "这是反诈模拟演示。有人在视频里声称是您的孙子，说出了事故，需要马上转账交手术费，还要求不要告诉其他家人。请暂停转账，通过提前保存的常用号码核实。",
    "expert-simulation": "这是反诈模拟演示。有人在视频里冒充专家，声称一种产品保证治好疾病，投资还能保本翻倍，并催您立即付款。请先核实身份和宣传依据。",
    "normal-synthetic-control": "这是普通内容的合成语音对照。奶奶您好，今天下午我们一起去公园散步，晚上回来吃饭，不涉及转账和验证码。",
    "guidance-contact-family": "核验已经完成。请注意，这份报告不能确认对方身份。请先不要转账，也不要提供验证码，再拨打提前保存的家人常用号码，独立核实。",
    "guidance-edited-image": "这张照片发现了需要核实的局部编辑线索。这不是已经证实的修改事实。请核实原始来源，不要仅凭照片决定转账。",
    "guidance-ai-image": "这张照片发现了需要核实的整图生成线索。请核实原始来源，不要仅凭照片决定转账。",
    "guidance-inconclusive": "目前没有取得明确的核验线索。这不代表内容真实，也不能确认对方身份。请通过提前保存的家人常用号码继续核实。",
}


async def main():
    root = bootstrap.ROOT / "data/demo"
    root.mkdir(parents=True, exist_ok=True)
    old = (
        json.loads((root / "source.json").read_text(encoding="utf-8")).get(
            "scripts", {}
        )
        if (root / "source.json").exists()
        else {}
    )
    for name, text in SCRIPTS.items():
        path = root / (name + ".mp3")
        if not path.exists() or old.get(name) != text:
            await edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural", rate="-10%").save(
                str(path)
            )
        print(name, path.stat().st_size, flush=True)
    artifacts = {
        p.name: {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size,
        }
        for p in root.glob("*.mp3")
    }
    (root / "source.json").write_text(
        json.dumps(
            {
                "provider": "Microsoft Edge TTS via edge-tts",
                "voice": "zh-CN-XiaoxiaoNeural",
                "label": "all synthetic; fictional anti-fraud simulations; not real impersonation",
                "scripts": SCRIPTS,
                "artifacts": artifacts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
