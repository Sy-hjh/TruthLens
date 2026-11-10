# 如何建立真正有效的评测

6条英语公开声音仅用于工程检查，因为与模型训练来源重叠，不能报告独立准确率。2.0另加6条MINDS14中文真人电话语音与3条自制合成语音，只是小样本试验，见ACCEPTANCE和DATASETS，不能作为老人场景总体成绩。
视频工程测试使用生成的运动色块片段，仅确认推理结构，不证明人脸检测能力。

需要另建授权素材集：真实亲人视频、已知换脸/口型驱动视频、真人/合成中文语音，覆盖老人声音、环境噪音、截图与平台压缩。
训练与测试按人物、原始视频和生成器隔离，不仅按文件名随机分开。
每一条要记录来源、许可、真实标签、生成器/处理方法，不能让通用LLM猜标签。

评测清单示例（JSON数组）：
```json
[
 {"path":"data/eval/real.mp4","label":"real","group":"person-source-001"},
 {"path":"data/eval/fake.mp4","label":"fake","group":"person-source-002"}
]
```
运行 `python evaluate_manifest.py data/video-test.json --kind video` 或 `--kind audio`。
报告写reports。每个group仅允许一个样本；预测失败单独列出，不能当作真实或静默删除。
正式比较不同模型时固定同一清单，报告FPR、FNR、Precision、Recall、F1、AUC与耗时。
固定0.5仅为初始基线；调阈值使用验证集，不能在最终测试集上挑最好结果。
当前evaluate_manifest.py的audio基线仅取每条前10秒；网站展示至多180秒各段，不把这个单段指标冒充整条材料的效果。

## 训练决定
本轮没有训练新模型，不是训练失败。没有独立领域评测前，训练无法证明比现有模型更好。
旧项目training/train.py及CIFAKE成绩不适用于本项目的视频与声音任务。
用户此前明确纠正过“不要擅自改为全参数微调”，因此本轮不替用户选择训练策略。
