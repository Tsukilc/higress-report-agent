# Higress Report Generator

AI-powered GitHub repository report generation tool for automated monthly reports and changelogs.

## 🚀 Quick Start

### Prerequisites

1. **Clone and build GitHub MCP Server**
```bash
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server
go build -o ../github-mcp-serve ./cmd/github-mcp-server
```

2. **Install dependencies**
```bash
uv sync
chmod +x ./github_proxy_mcp_server.py
```

3. **Configure environment variables**
```bash
# Required
export GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token
export DASHSCOPE_API_KEY=your_dashscope_api_key

# LLM Configuration
export MODEL_NAME=qwen-max
export MODEL_SERVER=https://dashscope.aliyuncs.com/compatible-mode/v1

# Optional
export GITHUB_REPO_OWNER=alibaba          # Default: alibaba
export GITHUB_REPO_NAME=higress           # Default: higress
export GOOD_PR_NUM=10                     # Number of highlighted PRs
```

### Usage

**Interactive Mode** (Recommended):
```bash
uv run python report_main.py
```

**Command Line Example**:
```python
from report_main import ReportAgent

agent = ReportAgent()

# Generate monthly report
agent.generate_monthly_report(month=4, year=2025)

# Generate changelog
agent.generate_changelog(pr_num_list=[1234, 1235, 1236])
```

## 📊 Features

- **🏢 Multi-Repository Support**: Works with any GitHub repository (alibaba/higress, etc.)
- **📝 Dual Report Types**: Monthly reports (time-filtered) + Changelogs (specific PR lists)
- **🤖 AI-Powered Analysis**: 129-point scoring system for automatic quality PR selection
- **🌍 Bilingual Output**: Automatically generates Chinese and English versions
- **⭐ Enhanced Important PRs**: Detailed patch analysis for important PRs
- **📁 Auto File Save**: Generates report.md + report.EN.md

## 🛠️ Utility Tools

### PR Link Extractor

Quickly extract PR numbers from GitHub links:

```python
# Example link: https://github.com/alibaba/higress/pull/1234
# Result: 1234

# Batch extraction (comma-separated):
# https://github.com/alibaba/higress/pull/1234,https://github.com/alibaba/higress/pull/1235
# Result: 1234,1235
```

In interactive mode, you can directly paste GitHub links and the system will automatically extract PR numbers.

## 🎯 Use Cases

| Scenario | Example                                            |
|----------|----------------------------------------------------|
| Monthly Report | `Generate Higress community report for April 2025` |
| Quick Changelog | Input PR list: `1234,1235,1236`                    |
| Important Release | Specify important PRs + regular PR list            |
                |

## ⚙️ How It Works

1. **Data Retrieval**: Calls GitHub MCP Server to fetch PR/Issue data
2. **AI Scoring**: LLM analyzes PR complexity, impact scope, code volume, etc.
3. **Smart Filtering**: Sorts by score and extracts quality content
4. **Report Generation**: Generates bilingual reports in predefined formats

## 📋 Notes

- **Token Usage**: Generating one monthly report requires ~100k tokens
- **Access Permissions**: Ensure GitHub Token has access to target repository
- **Recommendation**: Specify exact year/month to reduce unnecessary data fetching

---

📝 See [CONFIG.md](CONFIG.md) for detailed configuration instructions