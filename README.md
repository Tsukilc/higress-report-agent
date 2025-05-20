## 使用指南
创建.env文件

克隆官方github mcp 服务器，并生成二进制文件

````
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server # 上一步克隆下来的文件夹
go build -o ../github-mcp-serve ./cmd/github-mcp-server
````

编译运行
````
uv sync
chmod +x ./github_proxy_mcp_server.py
uv run ./main.py
````

示例提问：帮我生成higress社区2025年4月份的月报

nohup.txt可以看到调用的日志，运行进度等

## 环境变量
````
DASHSCOPE_API_KEY: (llmapikey)
GITHUB_PERSONAL_ACCESS_TOKEN= (github访问令牌)
MODEL_NAME= (模型名称) 
MODEL_SERVER= (模型服务地址)
GOOD_PR_NUM=10 (需要生成的亮点pr数)
````

## 运行原理
1. **数据获取**：
   - 调用GitHub Proxy MCP Server获取PR和Issue数据，支持分页和按月份过滤。
   - 使用增强工具`get_good_pull_requests`进行pr筛选，使用github-mcp-server进行issue筛选

2. **大模型评分**：
   - 使用LLM对PR进行评分，根据更改代码和pr描述，综合考虑技术复杂度、用户影响范围、代码量，pr类型等因素。
   - 评分结果按分数降序排列，提取前10个PR作为亮点功能。

3. **月报生成**：
   - 根据提取的PR和Issue数据，按照预定义格式生成月报内容到控制台。

## 注意
mcp调用次数非常多(每个pr都要调用mcp进行分析），token量消耗有点大，生成一个月周报预计得10万个token

使用时建议明确指定年月份，比如 帮我生成higress社区2025年4月份的月报

