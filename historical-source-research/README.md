# Historical Source Researcher · 历史史料检索与考证

版本 1.1.0。用于原始史料发现、出处核验、来源批判和命题匹配。直接输入 `$historical-source-research 寻找1971—1972年中美关系缓和期间领导人决策过程的史料，给我史料和文献矩阵、时间线及命题证据图。`

默认交付可离线筛选的 HTML、三份 CSV/Markdown 矩阵、三张 SVG 图、结构化记录和检索日志。研究文献与档案分别记录，摘要不冒充全文，图表不自动证明因果。主入口 SKILL.md，运行说明 references/visual-deliverables.md。

Python 3.10+，运行仅标准库：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/export_sources.py research-data.json --output-dir outputs/research
```

本地程序验证不能证明史料真实。网络受限时保留缺口并完成离线整理。1.1.0升级保留原有验证、引注、去重与日志能力，并新增默认可视化成品。

## GitHub 上传与安装

将本文件夹内的全部文件和子目录上传到 GitHub 仓库根目录，保持 `SKILL.md`、`agents/`、`assets/`、`references/`、`scripts/` 和 `tests/` 的相对位置。

本地安装时，将整个文件夹保存为 `~/.codex/skills/historical-source-research`；不能仅复制 `SKILL.md`。无需 API 密钥或第三方 Python 包，在线检索使用当前代理实际可用的工具。

`MANIFEST.sha256` 记录发布文件的校验和，不包含自身及运行缓存。
