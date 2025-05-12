import os
from qwen_agent.agents import Assistant
from qwen_agent.utils.output_beautify import typewriter_print
from dotenv import load_dotenv

# 系统指令，用于指导Agent如何处理PR和生成月报
SYSTEM_INSTRUCTION = '''
你是一个优秀的月报生成专家，擅长通过分析GitHub仓库中的PR和Issue，严格按照月报格式，为Higress社区生成高质量的月报。

## 月报生成工作流程：

1. 获取优质PR列表：
   - 使用github_proxy_mcp_serve的get_good_pull_requests工具来获取本月评分最高的PR列表
   - 必须传入参数：owner="alibaba", repo="higress", month=当前月份 ,year=当前年份 perPage=100
   - 此工具会自动对PR进行评分并返回最高质量的PR，你必须完整遍历返回的列表中的每一个PR，一个不漏地全部总结
   - 用户如果指定了优质pr链接，一定要加入亮点模块总结展示

2. 获取新手友好Issue：
   - 使用github mcp server的list_issues工具获取 labels 为"good first issue"的开放问题
   - 必须传入参数：owner="alibaba", repo="higress", state="open",labels = "good first issue",perPage=2

3. 生成高质量月报：
   - 遍历列表全部，逐个分析获取PR或Issue数据，总结输出
   - 遵循下面的月报格式生成内容，标题只输出一遍，内容用三级标题慢慢输出，功能名称必须凝练成中文
   - 确保内容的技术准确性和可读性，月报内容从title和body中，以及阅读code_changes的代码进行总结，技术看点和功能价值都应在30-50字

## 月报格式：
# higress社区月报
## ⚙️good first issue
### Issue标题 
- 相关issue：issue链接
- issue概要  
...

## 📌本月亮点功能
### {功能名称}
- 相关pr：链接
- 贡献者：[贡献者id](贡献者github首页地址)
- 技术看点：关键技术实现方式和原理 
- 功能价值：功能价值概要  
...

## 结语
- 月度进步概要
- 欢迎和感谢社区贡献

## 重要规则：
1. 本月亮点功能中，使用get_good_pull_requests而非list_pull_requests获取PR列表，这个工具会自动对PR进行评分和筛选，返回的都是优秀pr
2. **必须完整处理所有PR**: 你必须从get_good_pull_requests返回的结果中逐个处理每一个PR，一个也不能遗漏。如果返回了10个PR，就必须总结全部10个PR；如果返回了5个PR，就必须总结全部5个PR
3. **严禁选择性总结**: 绝对不能只选择其中几个PR进行总结，而必须遍历并展示返回的全部PR(total_count个)，确保月报完整展现所有优质贡献
4. 每项PR功能的技术看点和功能价值应该简洁明了，并且强调出功能的技术看点和价值，25-50字
5. 三级标题必须使用###前缀
6. 结语部分总结本月社区发展情况并鼓励更多贡献者参与
7. 用户输入本月，当月要调用get_current_year_month获取当前年月。用户输入数字年月则一定要遵循当作参数传递
8. get_good_pull_requests每次对话只需要调用一次
9. 生成完成结语后，不管结果如何，禁止再调用任何工具或生成额外内容，直接结束本轮对话
10. 在开始总结PR前，先记录返回的PR总数，然后确保你总结了相同数量的PR

higress社区github地址: https://github.com/alibaba/higress
'''

def init_agent_service():
    # llm_cfg = {
    #     # Use the model service provided by DashScope:
    #     'model': 'qwen3-235b-a22b',
    #     'model_type': 'qwen_dashscope',
    #
    #     # 'generate_cfg': {
    #     #     # When using the Dash Scope API, pass the parameter of whether to enable thinking mode in this way
    #     #     'enable_thinking': False,
    #     # },
    # }
    llm_cfg = {
        # Use the OpenAI-compatible model service provided by DashScope:
        'model': os.getenv('MODEL_NAME'),
        'model_server': os.getenv('MODEL_SERVER'),
        'api_key': os.getenv('DASHSCOPE_API_KEY'),

        'generate_cfg': {
            # When using Dash Scope OAI API, pass the parameter of whether to enable thinking mode in this way
            'extra_body': {
                'enable_thinking': False
            },
        },
    }
    # llm_cfg = {
    #     # Use your own model service compatible with OpenAI API by vLLM/SGLang:
    #     'model': 'Qwen/Qwen3-32B',
    #     'model_server': 'http://localhost:8000/v1',  # api_base
    #     'api_key': 'EMPTY',
    #
    #     'generate_cfg': {
    #         # When using vLLM/SGLang OAI API, pass the parameter of whether to enable thinking mode in this way
    #         'extra_body': {
    #             'chat_template_kwargs': {'enable_thinking': False}
    #         },
    #
    #         # Add: When the content is `<think>this is the thought</think>this is the answer`
    #         # Do not add: When the response has been separated by reasoning_content and content
    #         # This parameter will affect the parsing strategy of tool call
    #         # 'thought_in_content': True,
    #     },
    # }
    tools = [
        {
            'mcpServers': {  # You can specify the MCP configuration file
                'github-mcp-serve':{
                    'command': './github-mcp-serve',
                    "args": ["stdio", "--toolsets", "issues","--toolsets","pull_requests","--toolsets","repos"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                    }
                },
                'github-mcp-server-proxy':{
                    "command": "uv",
                    "args": ['run', './github_proxy_mcp_server.py',"stdio", "--toolsets", "issues","--toolsets","pull_requests","--toolsets","repos"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                    }
                }
            }
        },
    ]

    bot = Assistant(llm=llm_cfg,
                    system_message=SYSTEM_INSTRUCTION,
                    function_list=tools,
                    name='higress-report-agent',
                    description="我是Higress社区月报生成助手，可以分析GitHub仓库PR和Issue来生成高质量的社区月报！")

    return bot


def test(query: str = 'who are you?'):
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = [{'role': 'user', 'content': query}]
    response_plain_text = ''
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)


def app_tui():
    # Define the agent
    bot = init_agent_service()

    # Chat
    messages = []
    follow_up = (
        "请使用get_good_pull_requests获取{{{{用户输入或者当月}}}}月优质PR，并且一定要把返回的pr全部展示，参数：owner='alibaba', repo='higress', month={{{{用户输入或者当月}}}}，year={{{{用户输入年份或本年}}}}。"
        "然后使用get_good_first_issues获取新手友好Issue，参数：owner=alibaba, repo=higress, state=open,labels =good first issue ，since = {{当前月份第一天}}}}'。"
        "注意，这些操作一次对话只进行一次就够了，生成结语后立刻停止任何工具调用，结束对话"
        "")
    messages.append({'role': 'user', 'content': follow_up})

    # Chat
    while True:
        query = input('用户问题: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)


if __name__ == '__main__':
    load_dotenv()
    # test()
    app_tui()
    # app_gui()

