"""Bounded video sampling; timestamps derive from decoded frame indices."""

import cv2
from PIL import Image


def sample_video(path, limit=12):
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or count <= 0:
            raise ValueError("无法读取视频帧率或长度")
        duration = count / fps
        if duration > 180:
            raise ValueError("第一版支持 3 分钟以内视频")
        indices = sorted(
            set(
                round(i * (count - 1) / max(1, min(limit, count) - 1))
                for i in range(min(limit, count))
            )
        )
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, bgr = cap.read()
            if ok:
                frames.append(
                    (idx / fps, Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
                )
        if not frames:
            raise ValueError("没有可解码的视频帧")
        return duration, frames
    finally:
        cap.release()
