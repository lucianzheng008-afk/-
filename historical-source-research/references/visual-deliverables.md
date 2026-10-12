# 可直接查读的矩阵与图表

## 从自然语言到成品

1. 解析研究问题，建立史料需求与待证命题。
2. 实际检索相关档案和必要的研究文献，逐项记录查读范围和 provenance。只用当前真实检索结果；演示数据不得复制进真实研究。
3. 代理在任务输出目录填写 `research-data.json`。顶层 `sources` 为标准史料记录，`claims` 为命题记录，`search_log` 为实际检索日志；可加 `research_title`、`research_summary` 与 `literature`。沿用 source-record-template.json，文献字段见 literature-record-template.json 和 literature-record.schema.json。字段未知使用 null，数组未知用空数组；全文没读不得补写结论。
4. 在本技能目录执行 `python3 scripts/validate_sources.py /绝对路径/research-data.json`，然后 `python3 scripts/export_sources.py /绝对路径/research-data.json --output-dir /绝对路径/成果目录`。正常导出自动生成所有矩阵与图表，无需依赖安装或联网。
5. 检查 HTML、CSV、SVG 的数量与 JSON 一致，逐项检查证据指向、引文位置和关键出处。提供 HTML 链接并打开预览；同时提供用户需要的 CSV 和独立 SVG。

## 文件与使用

- `research-report.html`：自包含页面，双击即可离线使用。史料/文献页签、搜索、状态筛选、日期排序、筛选 CSV、复制史料脚注、展开卡片、打印。浏览器拒绝剪贴板时提供可手动复制的文本框。
- `source-matrix.csv` / `.md`：史料的名称、形成日期、作者、性质、收藏机构、档案号、核验、命题、用途、局限、原始链接。
- `literature-matrix.csv` / `.md`：研究文献作者、年份、刊物、问题、方法、摘要/全文层级、史料线索、相关命题。摘要查读仅可据摘要概括，需在 notes 标明；仅元数据或搜索线索不得填写方法/结论。
- `claim-matrix.csv` / `.md`：支持、部分支持、反证、无法判断与材料缺口；无史料命题也保留。
- `timeline.svg`：文书形成日期；保留年/月精度，未归一化的日期不强行定位。出版、解密、数字化日期不代替形成日期。
- `verification.svg`：本次内容核验层级计数，不是可信度评分或独立来源数。
- `claim-evidence.svg`：支持方向及直接/间接证明价值，悬停查看理由与局限。空白只表示尚未关联；版本共享来源不能算独立印证。
- `chart-data.json`：图表的可复核数据；原始结构化记录和日志仍须一同保存。

CSV 使用 UTF-8 BOM，可在 WPS/Excel 中打开；Markdown 为文本视图。SVG 可插入论文准备材料或幻灯片，不把研究辅助图当作已经证明的因果机制图。HTML 无外部字体、CDN、脚本和网络请求。停用 JavaScript 时图表、史料表和卡片仍可读，文献表使用独立 CSV。打印时建议选择宽纸或横向；长矩阵以 CSV 为完整阅读视图。

## 运行边界

脚本只验证结构、字段一致性及实际记录关联，不能独立鉴定史料真伪。没有联网能力时依然生成用户授权材料的矩阵与图；未执行检索留 planned/offline，空集合不画虚构节点。原始文件、编辑版本、译文与删节文本分别保留，图中计数不替代版本分析。
