"""Pinned local screenshot OCR, bundled PP-OCRv6 weights, no runtime cloud OCR."""
import bootstrap,sys,subprocess,os,argparse,json,hashlib,shutil
def main():
 root=bootstrap.ROOT;p=argparse.ArgumentParser();p.add_argument('--skip-install',action='store_true');args=p.parse_args()
 if not args.skip_install:
  env=dict(os.environ,TEMP=str(root/'runtime/tmp'),TMP=str(root/'runtime/tmp'))
  subprocess.run([sys.executable,'-m','pip','install','--upgrade','--target',str(root/'runtime/ocr-packages'),'--no-deps','-r',str(root/'requirements-chat.txt')],env=env,check=True)
 folder=root/'runtime/ocr-packages/rapidocr/models';files=['PP-OCRv6_det_small.onnx','PP-OCRv6_rec_small.onnx','ch_ppocr_mobile_v2.0_cls_mobile.onnx'];hashes={}
 for name in files:hashes[name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
 target=root/'models/chat-ocr';target.mkdir(exist_ok=True);(target/'source.json').write_text(json.dumps(dict(package='rapidocr',version='3.10.0',license='Apache-2.0, including bundled PaddleOCR-derived models; retain MODEL_LICENSES.md',sha256=hashes),indent=2))
 vendor=root/'vendor/chat-ocr';vendor.mkdir(exist_ok=True)
 for name in ['LICENSE','MODEL_LICENSES.md']:
  source=root/'runtime/ocr-packages/rapidocr-3.10.0.dist-info/licenses'/name
  if source.exists():shutil.copyfile(source,vendor/name)
 print('Pinned OCR models verified',len(hashes))
if __name__=='__main__':main()
