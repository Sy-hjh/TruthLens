"""Face location only; never computes or matches identity embeddings."""
import cv2,numpy as np
from bootstrap import ROOT
def face_views(images,margin=1.4):
    path=ROOT/'models/face-detector/model.onnx'
    if not path.exists():raise RuntimeError('人脸定位模型未安装')
    detector=cv2.FaceDetectorYN.create('onnx',path.read_bytes(),b'',(320,320),.8,.3,5000)
    output=[];detected=0
    for image in images:
        rgb=np.asarray(image.convert('RGB'));h,w=rgb.shape[:2];scale=min(1.,640/max(w,h));small=cv2.resize(rgb,(round(w*scale),round(h*scale)));detector.setInputSize((small.shape[1],small.shape[0]));_,faces=detector.detect(cv2.cvtColor(small,cv2.COLOR_RGB2BGR))
        if faces is None:output.append(image);continue
        face=max(faces,key=lambda f:f[2]*f[3]);x,y,bw,bh=face[:4]/scale;cx=x+bw/2;cy=y+bh/2;side=max(bw,bh)*margin
        box=(max(0,int(cx-side/2)),max(0,int(cy-side/2)),min(w,int(cx+side/2)),min(h,int(cy+side/2)))
        output.append(image.crop(box));detected+=1
    if detected<len(images)//2:raise ValueError('多数采样画面没有检出可用人脸，当前换脸模型不适用；声音仍可单独核验。')
    return output,detected
