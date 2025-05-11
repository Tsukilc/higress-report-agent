## 使用指南
创建.env文件
uv sync
chmod +x ./github_proxy_mcp_server.py
uv run ./main.py

采取tui模式
支持自定义模型

示例提问：帮我生成higress社区2025年4月份的月报

nohup.txt可以看到调用的日志，运行进度等

## 运行原理
1. **数据获取**：
   - 调用GitHub MCP Server获取PR和Issue数据，支持分页和按月份过滤。
   - 使用自定义工具`get_good_pull_requests`和`get_good_first_issues`进行数据筛选。

2. **大模型评分**：
   - 使用LLM对PR进行评分，综合考虑技术复杂度、用户影响范围、代码量，pr类型等因素。
   - 评分结果按分数降序排列，提取前10个PR作为亮点功能。

3. **月报生成**：
   - 根据提取的PR和Issue数据，按照预定义格式生成月报内容到控制台。

## 注意
mcp调用次数非常多(每个pr都要调用mcp进行分析），token量消耗有点大，生成一个月周报预计得10万个token
使用时建议明确指定年月份，比如 帮我生成higress社区2025年4月份的月报

