# TestPilot - 测试设计工作台

TestPilot 面向测试产品、测试工程师与中小型研发团队，将 PRD、用户故事或接口说明转成结构化测试资产：需求拆解、风险识别、验收标准、测试用例、覆盖追踪和自动化建议。

它强调三件事：结果可解释、需求与用例可追踪、无外部服务时仍可稳定演示。

## 直接运行

Windows 可双击 `start_testpilot.bat`，脚本会检查依赖、启动服务并打开浏览器。

也可以在终端运行：

```powershell
python -m pip install -r requirements.txt
python app.py
```

浏览器打开：`http://127.0.0.1:5000`

首页的“查看完整示例”可以直接生成一份团队任务看板测试报告，不需要 API Key。

## ChatECNU 配置

项目支持华东师范大学 ChatECNU 的 OpenAI-compatible 接口。在本地 `.env` 中配置：

```env
LLM_API_URL=https://chat.ecnu.edu.cn/open/api/v1
LLM_API_KEY=你的令牌
LLM_MODEL=ecnu-plus
```

重启服务后，首页会显示“已连接模型服务”，并提供“使用 AI 分析示例”入口。模型输出使用 ChatECNU 的 JSON Schema 结构化约束；调用异常或返回无效关联时，系统自动回退到本地引擎。

## 核心能力

- 将非结构化需求拆分为独立需求项，并识别分类和口径缺口
- 根据权限、数据敏感度、失败影响等信号判断高/中/低风险
- 为每项需求生成可验证验收标准
- 覆盖主流程、边界、异常与权限场景，映射 P0/P1/P2
- 给出自动化候选与接口优先建议
- 展示方案完整度、风险分布、场景结构和发布关注项
- 提供需求到用例的覆盖追踪矩阵
- 支持用例搜索、组合筛选和详情展开
- 历史分析保存在本地 SQLite
- 支持 CSV、JSON、Markdown 导出
- 可选接入 OpenAI-compatible LLM，失败时自动回退本地引擎

## 验证

```powershell
python -m unittest discover -s tests -v
```

## 技术结构

```text
Flask Web UI
├── app.py              路由、流程编排与导出
├── engine.py           可解释的本地分析引擎
├── llm_provider.py     可选的大模型适配器
├── db.py               SQLite 数据层
├── templates/          工作台与分析报告
├── static/             样式与交互
└── tests/              引擎与 Web 主流程测试
```

详细产品思路见 `PRODUCT.md`，面试讲解建议见 `INTERVIEW.md`。

## 公网部署（Render）

项目已包含 `Dockerfile` 与 `render.yaml`，可以作为 Render Web Service 部署：

1. 将项目推送到 GitHub 仓库，确认 `.env` 没有提交。
2. 在 Render 选择 **New > Blueprint**，连接该仓库。
3. 创建服务时填写受保护的 `LLM_API_KEY`，其余变量由 `render.yaml` 提供。
4. 部署完成后通过 Render 提供的 `https://...onrender.com` 地址访问。

生产服务使用 Gunicorn，监听平台提供的 `PORT`，并通过 `/healthz` 接受健康检查。ChatECNU 令牌只从服务端环境变量读取，不会发送到浏览器或写入镜像。

免费实例的本地 SQLite 数据可能在重新部署后重置，适合作品集演示。若需要长期保存分析历史，可在 Render 使用持久化磁盘并将 `DATABASE_PATH` 设置为挂载目录中的数据库文件。
