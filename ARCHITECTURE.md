# TestPilot 技术架构

## 分层

```text
Browser
  ↓
Flask UI / Route Layer
  ├── 本地规则分析引擎 engine.py
  ├── 可选 LLM 适配器 llm_provider.py
  ├── SQLite 数据层 db.py
  └── CSV / JSON / Markdown 导出
```

## 关键取舍

- Flask + 原生前端：降低安装和演示成本，保持单体项目易读。
- SQLite：无需额外服务即可保留历史记录，适合本地作品演示。
- 本地规则引擎：确定、可解释、可测试，保证核心流程不依赖网络。
- LLM 增强层：改善开放文本理解，但异常时自动回到本地路径。
- JSON 字段：MVP 便于快速迭代；进入多人生产环境后可拆分为项目、需求、用例、执行记录等规范化表。

## 数据结构

`analyses` 表保存项目名、原始需求、分析模式、需求 JSON、用例 JSON、汇总 JSON 和创建时间。需求和用例通过 `req_id` 建立可追踪关系。

## 可靠性策略

- 输入长度校验，阻止无效分析。
- LLM 调用超时和异常时自动降级。
- SQLite 连接在读写后显式关闭。
- 导出文件使用 UTF-8；CSV 带 BOM，兼容 Windows Excel。
- 引擎和 Web 主流程均有自动化测试。
