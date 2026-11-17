# TruthLens 真鉴参赛说明

学校：大连东软信息学院。团队：湖舟行。队长：胡瑾慧；队员：周宇航、陈浩翔。团队确认项目此前未发表或获奖。

项目通过 React、TypeScript 与 Vite 前端和 FastAPI 后端提供图片、声音、有声视频和聊天截图的内容核验，保留不同模型的独立证据，并提供资料检索和报告问答。后端入口为 backend/app.py；前端源码为 web/src；已构建页面在 frontend-next。模型与工具来源见 docs/THIRD_PARTY.md。

## 本机启动

Windows x64，Python 3.10。当前机器已准备 .venv；新电脑应建立 Python 3.10 环境后安装 requirements.txt，按 README.md 补齐模型和独立 DAF/OCR 运行目录。DAF 另需 albumentations 1.3.1，已加入清单。

```powershell
.\.venv\Scripts\python.exe run.py --host 0.0.0.0 --port 8010
```

电脑打开 http://127.0.0.1:8010；手机连接同一局域网并使用电脑 WLAN IPv4 地址。运行时不需要 Node.js；修改前端后在 web 中安装前端依赖并执行 npm run build。PyCharm 使用 .venv/Scripts/python.exe，脚本 run.py，工作目录为项目根，参数与上面相同。

## 材料与测试

demo 包含图片与音频对照，新增 av-real.mp4 和 av-fake.mp4 两段保留原音轨的视频。测试脚本 submission_check.py 执行真实接口和模型推理；submission 内保存结果、技术文档和录屏提交指南。精选素材只作回归，不能充当总体准确率。声音模型开头最多检查 4 秒；假视频的克隆音轨本次存在漏检。

## 原创与沿革

工作空间保留早期亲安名称的迭代记录。当前工程扩展为多场景 TruthLens，包含自建 Web、检测编排、时序适配、图片字段关联、核验问答和后台管理。开源模型、算法与运行库分别保留作者归属和许可，不宣称全部原创。是否存在独立前身参赛项目仍待团队确认。

## 配置与公开仓库

默认本地模式不需要在线 API 密钥。环境说明见 .env.example；可选在线助手配置位于 runtime/companion-model.json，不能公开实际密钥。首次管理员初始化码位于 runtime/admin-setup.txt，账号与报告保存在 runtime，均不能进入公开仓库。不要提交本地 .venv、.python、.packages、缓存及私人上传材料。保留真实 Git 提交历史；公开前审查历史中是否有敏感信息。

本地 LAN 地址不能代替公网在线演示。公开仓库、评审访问授权和最终官网提交由团队核对执行；本轮未代为公开发布。
