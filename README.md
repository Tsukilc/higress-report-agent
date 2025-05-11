创建.env文件

uv sync
chmod +x ./github_proxy_mcp_server.py
uv run ./main.py

支持tui+gui双模式

示例提问：帮我生成higress社区2025年4月份的月报

注意：mcp调用次数非常多，token量消耗有点大，生成一个月周报预计得10万-20万个token

nohup.txt可以看到调用的日志