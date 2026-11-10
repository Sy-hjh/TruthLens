"""Matched-content Mandarin diagnostic, real telephone recordings vs disclosed TTS."""
import bootstrap,json,hashlib,random,asyncio
from pathlib import Path
import pyarrow.parquet as pq
ROOT=bootstrap.ROOT
async def main():
 import edge_tts
 folder=ROOT/'data/audio-check';folder.mkdir(exist_ok=True);allrows=pq.read_table(ROOT/'data/chinese-human/raw.parquet').to_pylist()[6:];random.Random(42).shuffle(allrows);chosen=[];seen=set()
 for row in allrows:
  if row['transcription'] in seen:continue
  chosen.append(row);seen.add(row['transcription'])
  if len(chosen)==60:break
 records=[];voices=['zh-CN-XiaoxiaoNeural','zh-CN-YunxiNeural','zh-CN-YunjianNeural']
 for i,row in enumerate(chosen):
  real=folder/f'real-{i:03}.wav';real.write_bytes(row['audio']['bytes']);fake=folder/f'tts-{i:03}.mp3';voice=voices[i%len(voices)]
  if not fake.exists():
   temp=fake.with_suffix('.part');await edge_tts.Communicate(row['transcription'],voice).save(str(temp));temp.replace(fake)
  for path,label in [(real,0),(fake,1)]:records.append(dict(path=path.relative_to(ROOT).as_posix(),label=label,group=str(i),transcription=row['transcription'],generator=voice if label else 'human',sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  print('Matched Mandarin pair',i+1,'/60',flush=True)
 (folder/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 (folder/'source.json').write_text(json.dumps(dict(real='PolyAI/minds14',revision='40ce77cb32a384e4d50a568e1ec39ac804019d33',real_license='CC-BY-4.0',fake='Explicitly generated standard Edge neural TTS, three generic voices, no imitation of a specific person',note='60 matched utterance pairs; diagnostic only; speaker independence unknown; not modern voice-cloning benchmark; do not redistribute without applicable voice-service terms'),indent=2),encoding='utf-8')
if __name__=='__main__':asyncio.run(main())
