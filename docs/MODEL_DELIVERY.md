# 模型文件交付

本目录所述模型文件由项目持有人明确授权从其工作空间提交，用于本作品的评审复现。第三方模型不属于团队原创，其原始来源、作者声明与现存 LICENSE、NOTICE 保留在各模型目录和 THIRD_PARTY.md。此交付不构成商用授权；缺少明确许可的组件不得据此推定可商用或无限制再分发。发布范围仅为 models 文件夹，不包含账号、密钥、用户上传或私人训练数据。

完整文件与 SHA256 见 all-model-files.json，包括当前模型和本地保留的历史候选。models/verispoof 只含声明文件，本机没有该目录的权重，不把它冒称已上传。

## 获取和校验

先安装 Git LFS，再执行：

```powershell
git clone https://github.com/Sy-hjh/TruthLens.git
cd TruthLens
git lfs pull
python restore_models.py
```

超过 GitHub 单文件限制的 convnext.safetensors 保持原字节顺序拆为 part00 等文件；脚本按清单拼接并检查 SHA256，不修改权重。保留足够磁盘空间：下载模型约 8.59 GB，还原另需约 3.39 GB 临时空间。

不要把 LFS 指针当作已下载权重。校验失败应停止推理并检查下载完整性。独立 DAF/OCR 二进制环境和 vendor 推理源码仍需按 ENVIRONMENT.md 配置，此模型交付不代表整个 Windows 运行环境已打包。

LFS 下载受 GitHub 账户带宽配额影响。本次不购买额外存储或开通计费。权重尚在上传或远程下载校验未完成时，不得声称模型交付已验收。
