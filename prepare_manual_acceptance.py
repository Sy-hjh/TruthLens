"""Create labelled functional samples; never mix these into training or accuracy claims."""
import bootstrap,json,asyncio,hashlib
import edge_tts
async def main():
 root=bootstrap.ROOT;folder=root/'data/manual-acceptance';folder.mkdir(exist_ok=True)
 rows=json.loads((folder/'images.json').read_text(encoding='utf-8'))
 video=json.loads((root/'data/video-gend-final/manifest.json').read_text())[:6]
 rows.extend(dict(r,modality='video',provenance='RTFS-10K pinned revision in data/video-gend-final/planned.json; author labels') for r in video)
 audio=json.loads((root/'data/audio-check/manifest.json').read_text(encoding='utf-8'))
 rows.extend(dict(r,modality='audio',provenance='PolyAI/minds14 CC-BY-4.0; reused diagnostic samples, not independent benchmark') for r in [x for x in audio if x['label']==0][-2:])
 for i,(voice,text) in enumerate([('zh-CN-YunxiNeural','今天下午我们去公园走一走，回家后一起吃晚饭。'),('zh-CN-XiaoxiaoNeural','收到陌生短信，先核实来源，不要告诉别人短信验证码。')]):
  path=folder/f'new-generic-tts-{i}.mp3'
  if not path.exists():await edge_tts.Communicate(text,voice).save(str(path))
  rows.append(dict(path=path.relative_to(root).as_posix(),label=1,modality='audio',generator=voice,transcription=text,provenance='New generic Edge TTS, no specific person imitation; functional control only'))
 for row in rows:row['sha256']=hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
 (folder/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print('Prepared',len(rows),'labelled manual controls')
if __name__=='__main__':asyncio.run(main())
