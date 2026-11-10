import bootstrap,json,hashlib
from collect_domain_cases import get
from pathlib import Path
def main():
    root=bootstrap.ROOT/'models/face-detector';root.mkdir(exist_ok=True)
    repo='opencv/opencv_zoo';rev=get('https://api.github.com/repos/'+repo+'/commits/main').json()['sha'];name='models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
    pointer=get(f'https://raw.githubusercontent.com/{repo}/{rev}/{name}').text;expected=next(line.split('sha256:')[1] for line in pointer.splitlines() if line.startswith('oid sha256:'))
    data=get(f'https://media.githubusercontent.com/media/{repo}/{rev}/{name}').content
    if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Face detector hash mismatch')
    (root/'model.onnx').write_bytes(data);(root/'LICENSE').write_text(get(f'https://raw.githubusercontent.com/{repo}/{rev}/models/face_detection_yunet/LICENSE').text,encoding='utf-8')
    (root/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,sha256=expected,license='MIT',purpose='face location only, not identity or synthesis detection'),indent=2),encoding='utf-8');print('Verified face locator',len(data))
if __name__=='__main__':main()
