# 系统架构与代码规范

## 目录职责

| 目录 | 职责 |
|---|---|
| web/src | React/TypeScript 页面、公共 API、报告与助手组件 |
| frontend-next | 可直接由后端服务的生产构建文件 |
| backend/app.py | HTTP 入口、任务排队、分支调用与状态汇总 |
| backend/admin_api.py admin_store.py | 鉴权、权限和管理配置 |
| backend/ordered_video.py ast_voice.py fused_image.py daf_image.py | 独立检测器适配 |
| backend/agent_review.py rag.py | 只读工具调用、混合检索和来源校验 |
| models release | 当前模型配置、适配头及协议；大型资源单独准备 |
| vendor | 第三方组件与许可；未包含组件见环境说明 |
| docs | 架构、部署、来源与验收记录 |
| 根目录 train/evaluate/verify 脚本 | 历史训练、评测及复现入口，保留真实开发过程 |

## 数据流与接口约定

POST /api/analyze 经登录检查后返回 job_id；GET /api/jobs/{id} 查询进度；完成后生成独立模块报告。任务采用单队列，重模型由锁保护；ASR 有独立线程，取证分支使用子进程。报告读取和删除按 owner_id 校验，管理员操作单独鉴权。

分支使用 completed、unavailable、disabled 等明确状态；score 只能与该模块 threshold 比较，不能跨模型相加。工具轨迹展示执行步骤与状态，不公开隐藏思维链。模型结果不能确认人物身份。

## 代码维护约定

Python 使用模块拆分、snake_case 函数和明确异常边界；关键算法边界通过模块 docstring 与内联注释说明。TypeScript 使用类型化 API、页面组件及共享组件，保持接口字段可空性与失败状态兼容。注释解释采样、阈值、隔离和安全约束，不复述显然的代码。

提交前对修改文件做语法检查，执行相关单元测试和前端测试。更换模型时独立验证阈值与数据范围，保留失败案例。禁止在测试中根据文件名直接返回真伪，禁止为演示样本调整结论。历史实验脚本保留其用途，不应当成当前默认推理入口。
