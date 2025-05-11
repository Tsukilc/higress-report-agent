"""An agent implemented by assistant with qwen3"""
import os  # noqa
import datetime  # 新增

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent.utils.output_beautify import typewriter_print
from dotenv import load_dotenv


def get_current_time():
    """获取当前时间（ISO格式）"""
    return {"current_time": datetime.datetime.now().isoformat()}


# 系统指令，用于指导Agent如何处理PR和生成月报
SYSTEM_INSTRUCTION = '''
你是一个优秀的月报生成专家，擅长通过分析GitHub仓库中的PR和Issue，为Higress社区生成高质量的月报。

## PR重要性评估标准（总分129分）：

1. 技术复杂度 (49分)：
   - 高 (45-49分)：涉及核心架构变更、重要算法实现、跨组件重构，新功能实现
   - 低 (1-4分)：简单Bug修复、文档更新、配置修改

2. 用户影响范围 (20分)：
   - 高 (15-20分)：影响所有用户、核心功能改进、新增重要特性
   - 中 (5-14分)：影响部分用户、功能增强、可用性改进
   - 低 (1-4分)：影响少数用户、次要功能修复、内部改进

3. 代码量与复杂度 (60分)：
   - 代码行数变化很小的PR (<10行) 不能作为亮点功能，直接排除
   - 代码行数10-100行的PR，最高只能得到40分
   - 代码行数100-200行的PR，根据复杂度评分，获得50分
   - 代码行数200行以上且复杂度高的PR，获得60分

70分及以上的PR可以考虑作为亮点功能。

## PR分析流程 - 核心步骤：
1. 使用list_pull_requests（月报一定一定要输入当前月份）获取已合并的PR列表：
   - 使用参数：perPage=100, state=closed, sort=created, direction=desc，month = {用户输入月份}
   
2. 务必对每个PR(list_pull_requests返回的，一个_links代表存在一个pr，一个不能少)单独处理：
   - 调用get_pull_request_files获取文件变更信息
   - 计算总变更行数(additions+deletions)
   - 如果总变更行数<10，立即排除该PR
   - 根据PR信息和变更行数评分

3. 根据评分排序，选择9-12个分数最高的PR作为亮点功能

## 月报格式：
# higress社区月报
## ⚙️good first issue
### [编号] Issue标题 
- 相关issue：issue链接
- issue概要  

## 📌本月亮点功能
### 功能名称 
- 相关pr：链接
- 贡献者：[贡献者id](贡献者github首页地址)
- 技术看点：关键技术实现方式 
- 功能价值：功能价值概要  

## 结语
- 月度进步概要
- 欢迎和感谢社区贡献

## 重要规则：
1. good first issue从open状态issue中提取，参数：perPage=5, state=open, labels=good first issue
2. 不要展示草稿状态或未合并的PR
3. 评分严格按照上述标准执行，不能凭空想象或伪造数据
4. 三级标题必须使用###前缀
5. 技术看点，功能价值，结语，都要求50字左右

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
    query = input('user question: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    response_plain_text = ''
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)

    # 添加辅助提示，确保对每个PR单独处理
    if "生成" in query and ("月报" in query or "周报" in query):
        follow_up = "对每个PR都请单独调用get_pull_request_files API评估代码变更。注意总变更行数少于10行的PR直接排除。"
        print("\n系统提示: " + follow_up)
        messages.append({'role': 'user', 'content': follow_up})
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)

    # Chat
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        response_plain_text = ''
        for response in bot.run(messages=messages):
            response_plain_text = typewriter_print(response, response_plain_text)
        messages.extend(response)


def app_gui():
    # Define the agent
    bot = init_agent_service()
    chatbot_config = {
        'prompt.suggestions': [
            '生成higress社区2025年5月份的月报',
            '分析这个PR的技术价值：https://github.com/alibaba/higress/pull/1234',
            '本月有哪些适合新手的issues？'
        ]
    }
    WebUI(
        bot,
        chatbot_config=chatbot_config,
    ).run()


if __name__ == '__main__':
    load_dotenv()
    # test()
    app_tui()
    # app_gui()
