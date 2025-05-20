## Usage Guide

Create a .env file

Clone the official GitHub MCP server and generate the binary file:

```
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server # The folder cloned in the previous step
go build -o ../github-mcp-serve ./cmd/github-mcp-server
```

Compile and Run:

```
uv sync
chmod +x ./github_proxy_mcp_server.py
uv run ./main.py
```

Example Question: Generate the monthly report for the Higress community for April 2025.

You can view the invocation logs, progress, etc., in nohup.txt.

## Environment Variables

```
DASHSCOPE_API_KEY: (llmapikey)
GITHUB_PERSONAL_ACCESS_TOKEN= (GitHub access token)
MODEL_NAME= (Model name)
MODEL_SERVER= (Model server address)
GOOD_PR_NUM=10 (Number of highlight PRs to generate)
```

## Operating Principle

1. **Data Acquisition**:
   - Call the GitHub Proxy MCP Server to obtain PR and Issue data, supporting pagination and filtering by month.
   - Use the enhancement tool `get_good_pull_requests` to filter PRs and github-mcp-server to filter issues.
2. **Large Model Scoring**:
   - Use LLM to score PRs based on factors such as code changes, PR descriptions, technical complexity, user impact, code volume, and PR type.
   - The scoring results are sorted in descending order, and the top 10 PRs are extracted as highlight features.
3. **Monthly Report Generation**:
   - Generate the monthly report content to the console according to the predefined format based on the extracted PR and Issue data.

## Note

The number of MCP calls is very high (each PR needs to call MCP for analysis), and the token consumption is a bit large. Generating a monthly report is expected to consume 100,000 tokens.

When using, it is recommended to explicitly specify the year and month, such as "Generate the monthly report for the Higress community for April 2025".