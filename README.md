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

## 限制

- PDF 文本抽取依赖 `pypdf`。如果 PDF 是纯图片扫描件，当前版本不会做 OCR。
- OFD 解析优先读取常见税务/铁路/航空结构化字段；非常规 OFD 模板可能需要补充字段映射。
- Excel 输出使用标准库生成，偏重可读数据表，不做复杂样式。
