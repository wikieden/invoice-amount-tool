---
name: invoice-totaler
description: Summarize invoice amounts from PDF/OFD files, folders, zip archives, or 7z archives using the invoice-totaler CLI. Use when the user asks to total, classify, deduplicate, audit, export, or report invoice/fapiao/发票 amounts.
license: MIT
metadata:
  package: invoice-amount-tool
  command: invoice-totaler
  requires: shell, filesystem read/write, uv/pip/pipx, optional 7zz/7z/bsdtar
---

# Invoice Totaler

Use this skill to turn a pile of invoices into a classified amount summary and an audit-friendly output file.

## Workflow

1. Identify the input path from the user: a directory, a single `.pdf`/`.ofd`, `.zip`, or `.7z`.
2. Choose output format:
   - Default to `.xlsx` for user-facing summaries.
   - Use `.csv` or `.json` when the user asks for data interchange or automation.
   - Use `--category-rules RULES.json` when the user provides custom category names, reimbursement buckets, departments, projects, or keyword rules.
3. Ensure the CLI is available:
   ```bash
   command -v invoice-totaler || uv tool install invoice-amount-tool
   ```
   If `uv` cannot find a fresh PyPI package because of cache or mirror lag:
   ```bash
   uv tool install --default-index https://pypi.org/simple --refresh-package invoice-amount-tool invoice-amount-tool
   ```
   Check the local runtime when dependency health matters:
   ```bash
   invoice-totaler doctor
   ```
4. Run the tool:
   ```bash
   invoice-totaler INPUT_PATH -o OUTPUT.xlsx
   ```
   Use strict mode for reimbursement, audit, CI, or automated agent workflows:
   ```bash
   invoice-totaler INPUT_PATH --strict -o OUTPUT.xlsx
   ```
   For custom categories:
   ```bash
   invoice-totaler INPUT_PATH --category-rules RULES.json -o OUTPUT.xlsx
   ```
   For alternate formats:
   ```bash
   invoice-totaler INPUT_PATH --format json -o summary.json
   invoice-totaler INPUT_PATH --format csv -o summary.csv
   ```
5. Verify output exists and read the command summary. Exit code `2` in strict mode means the report was written but at least one invoice needs review.
6. For `.xlsx`, confirm it is a valid zip or open/import it when the environment supports spreadsheet inspection.
7. Report the key totals, unique invoice count, output path, and any caveats. Always mention `problem_count` or the `问题清单` sheet when present.

## Platform Notes

- Codex: install with `$skill-installer`, invoke as `$invoice-totaler`.
- Claude Code: copy or install the folder to `~/.claude/skills/invoice-totaler` or `.claude/skills/invoice-totaler`, then invoke as `/invoice-totaler`.
- Kiro: import the GitHub skill-folder URL or copy the folder to `~/.kiro/skills/invoice-totaler` or `.kiro/skills/invoice-totaler`.
- OpenCode: copy the folder to `~/.config/opencode/skill/invoice-totaler`, `.opencode/skill/invoice-totaler`, or use the Claude-compatible `~/.claude/skills/invoice-totaler` path.
- OpenClaw, Hermes, and other Agent Skills hosts: import the GitHub skill-folder URL or copy this `SKILL.md` directory to the host's global/project skills path.
- The skill deliberately delegates parsing to the published `invoice-totaler` CLI, so any host only needs shell access and normal filesystem read/write access.

## Output Expectations

- Preserve currency separation. Do not convert USD/CNY unless the user explicitly asks and provides a rate or requests live lookup.
- Mention that duplicate PDF/OFD copies are deduplicated by invoice number.
- Inspect low-confidence/problem rows when available. JSON includes `problem_count` and `problem_rows`; XLSX includes a `问题清单` sheet; detail rows include `amount_source`, `confidence`, and `issues`.
- Custom category rules are JSON. Rules match in order and take priority over built-in categories. A rule can contain `category`, `path_contains`, and/or `text_contains`; both path and text conditions must match when both are present.
- For `.7z`, the system needs `7zz`, `7z`, or `bsdtar`; if unavailable, ask for an extracted folder or install an archive tool.
- For image-only scanned PDFs, explain that the current CLI does not perform OCR.

## Amount Policy

For detailed amount-selection rules, read [references/amount-policy.md](references/amount-policy.md) when the user asks about auditability, reimbursement policy, or why a number was chosen.

## Examples

```bash
invoice-totaler ~/Desktop/发票.7z -o 发票金额分类统计.xlsx
invoice-totaler ~/Desktop/发票.7z --strict -o 发票金额分类统计.xlsx
invoice-totaler ~/Desktop/发票.7z --category-rules category-rules.json -o 发票金额分类统计.xlsx
invoice-totaler ./发票 -o 发票金额分类统计.xlsx
invoice-totaler ./发票/单张发票.ofd --format json -o summary.json
invoice-totaler doctor
```
