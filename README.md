# invoice-amount-tool

一个用于统计发票金额的命令行工具。它可以读取目录、单个 PDF/OFD 文件，或 `.zip` / `.7z` 压缩包，提取发票金额，按发票号去重，并按分类汇总导出。

当前内置分类包括：

- 房租
- 火车票
- 机票
- 餐饮
- Apple 礼品卡
- 其他

## 金额口径

- 中文普通/专用发票：取含税总额，也就是价税合计小写金额。
- 火车票：取票价。
- 机票：取合计金额，不取单独票价。
- Apple 发票：保留 USD，不做汇率换算。
- 同一发票号同时存在 PDF/OFD 时只统计一次，并优先采用结构化 OFD 字段。

## 安装

从 PyPI 安装：

```bash
python -m pip install invoice-amount-tool
```

推荐用 `uv` 安装成独立命令行工具：

```bash
uv tool install invoice-amount-tool
```

如果你的 `uv` 使用了镜像源或缓存，刚发布的新包可能暂时找不到；可以强制走官方 PyPI 并刷新这个包：

```bash
uv tool install --default-index https://pypi.org/simple --refresh-package invoice-amount-tool invoice-amount-tool
```

也可以用 `pipx` 安装成独立命令行工具：

```bash
pipx install invoice-amount-tool
```

从 GitHub Release 安装 wheel：

```bash
python -m pip install https://github.com/wikieden/invoice-amount-tool/releases/download/v0.1.0/invoice_amount_tool-0.1.0-py3-none-any.whl
```

用 `pipx` 安装成独立命令行工具：

```bash
pipx install https://github.com/wikieden/invoice-amount-tool/releases/download/v0.1.0/invoice_amount_tool-0.1.0-py3-none-any.whl
```

从源码安装：

```bash
python -m pip install .
```

开发模式：

```bash
python -m pip install -e .
```

`.7z` 压缩包需要系统里有 `7zz`、`7z` 或 `bsdtar` 任意一个命令。也可以先手动解压，然后把目录传给工具。

## 使用

导出 Excel：

```bash
invoice-totaler ~/Desktop/发票.7z -o 发票金额分类统计.xlsx
```

导出 CSV：

```bash
invoice-totaler ~/Desktop/发票.7z --format csv -o 发票金额分类统计.csv
```

导出 JSON：

```bash
invoice-totaler ~/Desktop/发票.7z --format json -o 发票金额分类统计.json
```

也可以直接处理目录：

```bash
invoice-totaler ./发票 -o 发票金额分类统计.xlsx
```

或处理单个 PDF/OFD 文件：

```bash
invoice-totaler ./发票/火车票/26949134178000969211.ofd -o 单张发票统计.xlsx
```

## 作为 Codex Skill 使用

仓库内置了一个 Codex agent skill。推荐在 Codex 里用 `$skill-installer` 从 GitHub 安装：

```text
$skill-installer install https://github.com/wikieden/invoice-amount-tool/tree/main/skills/invoice-totaler
```

安装后重启 Codex，让新 skill 被加载。

也可以在 shell 里用 Codex 自带安装脚本安装：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/wikieden/invoice-amount-tool/tree/main/skills/invoice-totaler
```

手动安装方式：

```bash
mkdir -p ~/.codex/skills
cp -R skills/invoice-totaler ~/.codex/skills/invoice-totaler
```

安装后可以在新会话里显式调用：

```text
$invoice-totaler 统计这个压缩包里的发票金额
```

### 作为 Claude Code Skill 使用

Claude Code 也支持 Agent Skills。把同一个目录复制到 Claude 的 skills 目录即可：

```bash
mkdir -p ~/.claude/skills
git clone --depth 1 https://github.com/wikieden/invoice-amount-tool.git /tmp/invoice-amount-tool
cp -R /tmp/invoice-amount-tool/skills/invoice-totaler ~/.claude/skills/invoice-totaler
```

然后在 Claude Code 里调用：

```text
/invoice-totaler 统计这个压缩包里的发票金额
```

这个 skill 的 frontmatter 包含 `allowed-tools: Bash Read Write`。这是 Claude Code 支持的扩展字段，用于在 skill 激活时预批准基础 shell / 文件读写工具；其他 Agent Skills host 不支持时会忽略它。

### Skill 发布渠道

- 当前发布位置：本仓库的 `skills/invoice-totaler` 目录。
- Codex 官方技能目录：可以考虑向 [`openai/skills`](https://github.com/openai/skills) 提 PR；该仓库支持 curated/experimental skills，并可通过 `$skill-installer` 安装。
- Agent Skills 标准：[`agentskills.io`](https://agentskills.io/) 是 SKILL.md 格式规范与生态入口。
- 社区目录：可补充提交到支持 GitHub repo 索引的社区 skill registry，例如 SkillHub、OmniSkill、AgentSkills 等。提交前应确认 registry 的安全/审核/溯源机制。

输出的 Excel 包含 3 个页签：

- `总览`：分类汇总和币种总计
- `明细`：去重后的每张发票
- `重复文件`：被合并的重复 PDF/OFD 文件

## 开发

运行测试：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

本地用样例压缩包验证：

```bash
PYTHONPATH=src python -m invoice_amount_tool ~/Desktop/发票.7z -o /tmp/invoice-summary.xlsx
```

## GitHub 发布建议

```bash
git init
git add .
git commit -m "Package invoice amount summariser as a CLI tool"
git branch -M main
git remote add origin git@github.com:<your-name>/invoice-amount-tool.git
git push -u origin main
```

## PyPI 发布

仓库包含 `.github/workflows/publish-pypi.yml`，支持 PyPI Trusted Publishing。

首次发布新项目时，在 PyPI 账号的 Publishing 页面添加 Pending Publisher：

- PyPI project name: `invoice-amount-tool`
- Owner: `wikieden`
- Repository name: `invoice-amount-tool`
- Workflow name: `publish-pypi.yml`
- Environment name: `pypi`

保存后，到 GitHub Actions 里手动运行 `Publish to PyPI` 工作流即可发布当前版本。

## 限制

- PDF 文本抽取依赖 `pypdf`。如果 PDF 是纯图片扫描件，当前版本不会做 OCR。
- OFD 解析优先读取常见税务/铁路/航空结构化字段；非常规 OFD 模板可能需要补充字段映射。
- Excel 输出使用标准库生成，偏重可读数据表，不做复杂样式。
