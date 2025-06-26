# Higress 报告生成器

基于 AI 的 GitHub 仓库报告生成工具，支持自动生成月报和 Changelog。

## 🚀 快速开始

### 环境准备

1. **克隆并编译 GitHub MCP 服务器**
```bash
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server
go build -o ../github-mcp-serve ./cmd/github-mcp-server
```

2. **安装依赖**
```bash
uv sync
chmod +x ./github_proxy_mcp_server.py
```

3. **配置环境变量**
```bash
# 必需配置
export GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token
export DASHSCOPE_API_KEY=your_dashscope_api_key

# LLM 配置
export MODEL_NAME=qwen-max
export MODEL_SERVER=https://dashscope.aliyuncs.com/compatible-mode/v1

# 可选配置
export GITHUB_REPO_OWNER=alibaba          # 默认：alibaba
export GITHUB_REPO_NAME=higress           # 默认：higress
export GOOD_PR_NUM=10                     # 月报亮点PR数量
```

### 运行

**交互模式**（推荐）：
```bash
uv run python report_main.py
```

**命令行示例**：
```python
from report_main import ReportAgent

agent = ReportAgent()

# 生成月报
agent.generate_monthly_report(month=4, year=2025)

# 生成 Changelog
agent.generate_changelog(pr_num_list=[1234, 1235, 1236])
```

## 📊 功能特性

- **🏢 多仓库支持**：支持任意 GitHub 仓库（alibaba/higress、microsoft/vscode 等）
- **📝 双报告类型**：月报（按时间筛选）+ Changelog（指定PR列表）
- **🤖 AI 智能分析**：评分系统自动筛选优质PR
- **🌍 双语输出**：自动生成中英文版本
- **⭐ 重要PR增强**：支持重要PR的详细patch分析
- **📁 文件自动保存**：report.md + report.EN.md

## 🛠️ 实用工具

### PR链接提取器

extract_pr_numbers.py，从包含GitHub链接长文本提取PR编号：





## ⚙️ 工作原理

1. **数据获取**：调用 GitHub MCP Server 获取 PR/Issue 数据
2. **AI 评分**：LLM 分析PR复杂度、影响范围、代码量等
3. **智能筛选**：按评分排序，提取优质内容
4. **报告生成**：按预定格式生成中英文报告

## 📋 注意事项

- **访问权限**：确保GitHub Token有目标仓库访问权限
- **建议**：明确指定年月份以减少不必要的数据获取

---

📝 详细配置说明见 [CONFIG.md](CONFIG.md)

