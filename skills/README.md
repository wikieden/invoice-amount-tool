# Skills

## invoice-totaler

Install in Codex with:

```text
$skill-installer install https://github.com/wikieden/invoice-amount-tool/tree/main/skills/invoice-totaler
```

Then restart Codex and invoke:

```text
$invoice-totaler 统计这个压缩包里的发票金额
```

Install in Claude Code with:

```bash
mkdir -p ~/.claude/skills
git clone --depth 1 https://github.com/wikieden/invoice-amount-tool.git /tmp/invoice-amount-tool
cp -R /tmp/invoice-amount-tool/skills/invoice-totaler ~/.claude/skills/invoice-totaler
```

Then invoke in Claude Code:

```text
/invoice-totaler 统计这个压缩包里的发票金额
```

Install in Kiro by importing this GitHub folder URL:

```text
https://github.com/wikieden/invoice-amount-tool/tree/main/skills/invoice-totaler
```

Or copy it manually:

```bash
mkdir -p ~/.kiro/skills
git clone --depth 1 https://github.com/wikieden/invoice-amount-tool.git /tmp/invoice-amount-tool
cp -R /tmp/invoice-amount-tool/skills/invoice-totaler ~/.kiro/skills/invoice-totaler
```

Install in OpenCode:

```bash
mkdir -p ~/.config/opencode/skill
git clone --depth 1 https://github.com/wikieden/invoice-amount-tool.git /tmp/invoice-amount-tool
cp -R /tmp/invoice-amount-tool/skills/invoice-totaler ~/.config/opencode/skill/invoice-totaler
```

OpenCode also discovers Claude-compatible skill locations such as `~/.claude/skills/invoice-totaler`.

The skill delegates deterministic invoice parsing to the `invoice-totaler` CLI from the `invoice-amount-tool` PyPI package.
