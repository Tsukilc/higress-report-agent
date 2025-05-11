"""
GitHub MCP服务器 - 使用FastMCP框架

这个服务器可以接受LLM调用，并转发请求到GitHub的MCP服务器。
主要功能是提供GitHub PR列表查询能力。
"""
import logging
import os
import subprocess
import json
import datetime
import re
import sys
from dateutil import parser as date_parser
from fastmcp import FastMCP
from typing import Optional,Dict, Any
from dotenv import load_dotenv

# 创建FastMCP服务器实例
mcp = FastMCP("GitHub PR查询服务")


def setup_logging():
    """
    设置日志记录器，同时输出到控制台和文件
    """
    # 创建日志文件目录（如果不存在）
    log_file = "./nohup.txt"

    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


    # 重定向 print 输出到日志文件
    original_print = print

    def print_to_log(*args, **kwargs):
        # 原始 print 功能保留
        original_print(*args, **kwargs)
        # 同时写入日志
        message = " ".join(map(str, args))
        logging.info(message)

    # 替换全局 print 函数
    globals()['print'] = print_to_log


# 在 if __name__ == "__main__": 前调用
setup_logging()



def remove_unwanted_urls(data):
    """
    递归移除数据中不需要的URL字段（更彻底的实现）

    Args:
        data: 要处理的数据(字典或列表)

    Returns:
        处理后的数据
    """
    if isinstance(data, dict):
        # 创建一个新字典，只保留需要的字段
        result = {}
        for key, value in list(data.items()):
            # 跳过以_url结尾且不是html_url的键
            if key.endswith("_url") and key != "html_url":
                continue

            # 递归处理嵌套数据
            if isinstance(value, (dict, list)):
                result[key] = remove_unwanted_urls(value)
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        # 递归处理列表中的每个元素
        return [remove_unwanted_urls(item) for item in data]
    else:
        # 如果既不是字典也不是列表，直接返回原值
        return data


def extract_month_from_date(date_str):
    """
    从日期字符串中安全地提取月份
    支持多种日期格式

    Args:
        date_str: 日期字符串

    Returns:
        提取的月份(1-12)或None(如果解析失败)
    """

    if not date_str:
        return None

    try:
        # 方法1: 使用标准ISO格式解析
        try:
            # 处理ISO格式 (2025-05-10T01:54:32Z)
            if 'T' in date_str and (date_str.endswith('Z') or '+' in date_str):
                dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.month
        except ValueError:
            pass

        # 方法2: 使用正则表达式匹配年-月-日格式
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if date_match:
            month = int(date_match.group(2))
            if 1 <= month <= 12:
                return month

        # 方法3: 使用dateutil解析器(最灵活但最慢的方法)
        dt = date_parser.parse(date_str)
        return dt.month

    except Exception:
        # 捕获所有异常，确保程序不会崩溃
        return None


def filter_prs_by_month(prs_data, month):
    """
    根据月份过滤PR列表

    Args:
        prs_data: PR数据列表
        month: 目标月份(1-12)

    Returns:
        过滤后的PR列表
    """
    if not month or not isinstance(prs_data, list):
        return prs_data

    filtered_prs = []

    for pr in prs_data:
        merged_at = pr.get("merged_at")

        # 如果没有merged_at字段或为null，则跳过
        if not merged_at:
            continue

        # 提取月份
        pr_month = extract_month_from_date(merged_at)

        # 检查月份是否匹配
        if pr_month is not None and pr_month == month:
            filtered_prs.append(pr)

    return filtered_prs


# def process_pull_requests(prs_data, month=None):
#     """
#     处理PR数据：移除不需要的URL字段并根据月份过滤
#
#     Args:
#         prs_data: 原始PR数据
#         month: 目标月份(1-12)，如果为None则不过滤
#
#     Returns:
#         处理后的PR数据
#     """
#     # 先移除不需要的URL字段
#     cleaned_data = remove_unwanted_urls(prs_data)
#
#
#     # 根据月份过滤PR
#     if month is not None:
#         filtered_data = filter_prs_by_month(cleaned_data, month)
#         return filtered_data
#
#     return cleaned_data


@mcp.tool()
def get_good_pull_requests(
        owner: str,  # 必填，仓库所有者
        repo: str,  # 必填，仓库名称
        state: Optional[str] = "closed",  # 可选，默认为closed，PR状态：open/closed/all
        head: Optional[str] = None,  # 可选，按头用户/组织和分支过滤
        base: Optional[str] = None,  # 可选，按基础分支过滤
        sort: Optional[str] = "created",  # 可选，排序方式：created/updated/popularity/long-running
        direction: Optional[str] = "desc",  # 可选，排序方向：asc/desc
        month: Optional[int] = None,  # 可选，按合并PR的月份过滤(1-12)
        page: Optional[int] = 1,  # 可选，页码
        perPage: Optional[int] = 50  # 可选，每页结果数，默认增加到50以获取更多数据
) -> Dict:
    """
    增强版列出GitHub仓库中的PR请求，可以筛选出合并的请求和指定月份的请求，并进行评分筛选。
    此处返回的pr已经处理好，必须全部提取展示

    Args:
        owner: 仓库所有者名称
        repo: 仓库名称
        state: PR状态过滤(open/closed/all)，默认为closed
        head: 按头用户/组织和分支过滤
        base: 按基础分支过滤
        sort: 排序方式(created/updated/popularity/long-running)
        direction: 排序方向(asc/desc)
        month: 按合并PR的月份过滤(1-12)
        page: 页码，从1开始
        perPage: 每页结果数，默认50

    Returns:
        包含评分后筛选的PR列表信息的字典
    """
    # 构建参数字典，仅包含非None值
    params = {
        "owner": owner,
        "repo": repo,
        "state": state,
        "sort": sort,
        "direction": direction,
        "page": page,
        "perPage": perPage
    }

    # 添加可选参数
    if head is not None:
        params["head"] = head
    if base is not None:
        params["base"] = base

    # 如果没有指定月份，使用当前月份
    if month is None:
        current_month = datetime.datetime.now().month
        month = current_month
        print(f"未指定月份，使用当前月份: {month}")

    # 尝试获取足够的PR数据
    tool_name = "list_pull_requests"

    # 先获取第一页
    print("获取PR第{page}页数据...")
    result = call_github_mcp_tool(tool_name, params)


    # 提取PR列表
    pr_list = filter_prs_by_month(result, month)

    # 初始化大模型评分队列
    scored_prs = []

    # 导入必要的模块
    from qwen_agent.agents import Assistant

    # 创建一个专门用于PR评分的助手
    scoring_system = """
    你是一个专业的PR评分助手，严格根据以下标准，逐步骤对PR进行评分（总分129分）：

    1. 技术复杂度 (50分)：
       - 高 (40-50分)：涉及核心架构变更、重要算法实现、跨组件重构、新功能实现
       - 中 (20-39分)：功能增强、复杂的Bug修复
       - 低 (1-19分)：简单Bug修复、配置修改，文档类pr，bot发布的pr

    2. 用户影响范围 (40分)：
       - 高 (30-40分)：影响所有用户、核心功能改进、新增重要特性
       - 中 (15-29分)：影响部分用户、功能增强、可用性改进
       - 低 (1-14分)：影响少数用户、次要功能修复、内部改进

    3. 代码量与复杂度 (30分)：
       - 代码行数变化很小的PR (<10行) 不能作为亮点功能，直接排除
       - 文档类PR直接排除，不计分
       - 代码行数10-100行的PR，最高只能得到20分
       - 代码行数100行以上且复杂度高的PR，获得25-30分

    4. Bug重要性 (9分)：
       - 高 (7-9分)：修复严重影响用户体验或系统稳定性的Bug
       - 中 (4-6分)：修复中等影响的Bug
       - 低 (1-3分)：修复轻微问题或边缘情况

    请根据以上标准对PR进行评分，并返回一个1-129之间的整数分数，无需解释。
    """

    # 初始化评分助手
    llm_cfg = {
        'model': os.getenv('MODEL_NAME'),
        'model_server': os.getenv('MODEL_SERVER'),
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
    }

    scoring_bot = Assistant(llm=llm_cfg, system_message=scoring_system)
    
    # 对每个PR进行评分
    for i, pr in enumerate(pr_list):
        # 跳过草稿PR
        if pr.get("draft", False):
            print(f"跳过草稿PR #{pr.get('number')}: {pr.get('title', '')}")
            continue
            
        # 跳过未合并的PR
        if not pr.get("merged_at"):
            print(f"跳过未合并的PR #{pr.get('number')}: {pr.get('title', '')}")
            continue
            
        pr_number = pr.get("number")
        if not pr_number:
            continue

            
        print(f"正在处理PR #{pr_number}: {pr.get('title', '')} ({i+1}/{len(pr_list)})")
        
        # 获取PR文件变更信息
        files_params = {
            "owner": owner,
            "repo": repo,
            "pullNumber": pr_number
        }
        
        try:
            files_result = call_github_mcp_tool("get_pull_request_files", files_params)
            
            # 检查文件变更结果
            if not isinstance(files_result, list):
                print(f"获取PR #{pr_number}文件变更失败: {files_result}")
                continue
                
            # 计算总变更行数
            total_changes = 0
            for file_info in files_result:
                total_changes += file_info.get("additions", 0) + file_info.get("deletions", 0)
                
            print(f"PR #{pr_number}总变更行数: {total_changes}")
            
            # 如果总变更行数小于10，则直接排除
            if total_changes < 10:
                print(f"PR #{pr_number}变更行数({total_changes})小于10，跳过")
                continue
            
            # 准备PR信息以发送给大模型评分
            pr_info = {
                "title": pr.get("title", ""),
                "body": pr.get("body", "")[:500] if pr.get("body") else "",  # 截取前500字符，避免太长
                "total_changes": total_changes,
                "file_changes": [
                    {
                        "filename": file.get("filename", ""),
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    } for file in files_result[:10]  # 限制文件数量，避免超出上下文长度
                ]
            }

            # 准备评分请求
            score_prompt = f"""
                请评分以下PR（总分129分）:

                PR标题: {pr_info['title']}
                PR描述: {pr_info['body']}
                总变更行数: {pr_info['total_changes']}
                文件变更 (前10个文件):
                {json.dumps(pr_info['file_changes'], indent=2, ensure_ascii=False)}

                根据PR内容和文件变更情况，给出1-129之间的整数评分。
                """

            # 使用大模型评分
            messages = [{'role': 'user', 'content': score_prompt}]
            response_text = ""

            for response in scoring_bot.run(messages=messages):
                if isinstance(response, list) and len(response) > 0:
                    for msg in response:
                        if msg.get('role') == 'assistant' and msg.get('content'):
                            response_text += msg.get('content', "")

            # 尝试从响应中提取分数
            try:
                # 查找响应文本中的数字
                import re
                score_match = re.search(r'\b(\d{1,3})\b', response_text)
                if score_match:
                    score = int(score_match.group(1))
                    # 确保分数在有效范围内
                    score = max(1, min(score, 129))
                else:
                    # 如果无法提取分数，则使用备用评分机制
                    if total_changes < 50:
                        score = 20 + (total_changes - 10) // 2  # 20-40分
                    elif total_changes < 100:
                        score = 40 + (total_changes - 50) // 5  # 40-50分
                    elif total_changes < 200:
                        score = 50 + (total_changes - 100) // 10  # 50-60分
                    else:
                        score = 70 + min(total_changes // 100, 30)  # 70-100分
            except:
                # 异常情况下的备用评分
                if total_changes < 50:
                    score = 20 + (total_changes - 10) // 2  # 20-40分
                elif total_changes < 100:
                    score = 40 + (total_changes - 50) // 5  # 40-50分
                elif total_changes < 200:
                    score = 50 + (total_changes - 100) // 10  # 50-60分
                else:
                    score = 70 + min(total_changes // 100, 30)  # 70-100分
            
            print(f"PR #{pr_number}评分完成，得分: {score}")
            
            # 添加到评分结果列表
            scored_pr = {
                "number": pr_number,
                "title": pr.get("title", ""),
                "html_url": pr.get("html_url", ""),
                "user": remove_unwanted_urls(pr.get("user", {})),
                "body": pr.get("body", "")[:500] if pr.get("body") else "",  # 限制PR描述长度
                "created_at": pr.get("created_at", ""),
                "merged_at": pr.get("merged_at", ""),
                "changes": total_changes,
                "score": score
            }
            scored_prs.append(scored_pr)
            
        except Exception as e:
            print(f"处理PR #{pr_number}时发生错误: {str(e)}")
            continue
    
    # 按评分降序排序
    scored_prs.sort(key=lambda x: x["score"], reverse=True)
    
    # 取评分最高的前10个
    top_prs = scored_prs[:10]
    
    print(f"评分完成，共有{len(scored_prs)}个PR，选出前{len(top_prs)}个")
    
    # 构建并返回结果
    return {
        "total_count": len(top_prs),
        "items": top_prs
    }


def call_github_mcp_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用GitHub MCP工具（非异步方式）

    Args:
        tool_name: 工具名称
        params: 参数字典

    Returns:
        API调用结果
    """
    # 设置环境变量
    env = os.environ.copy()
    if "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
        return {"error": "缺少GITHUB_PERSONAL_ACCESS_TOKEN环境变量"}

    # 构建JSON-RPC请求
    request = {
        "jsonrpc": "2.0",
        "id": 233,  # 随机ID
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }

    try:
        # 启动进程
        process = subprocess.Popen(
            ["./github-mcp-serve", "stdio", "--toolsets", "pull_requests"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )

        # 发送请求并获取响应
        stdout, stderr = process.communicate(input=json.dumps(request) + "\n")

        if process.returncode != 0:
            return {"error": f"命令执行失败: {stderr}"}

        try:
            # 简单解析，确保是有效的JSON
            raw_response = json.loads(stdout)

            # 针对GitHub MCP工具返回的特殊格式做简单处理
            if "result" in raw_response:
                # 尝试提取工具真正的返回结果
                try:
                    if "content" in raw_response["result"]:
                        for item in raw_response["result"]["content"]:
                            if item.get("type") == "text" and item.get("text"):
                                try:
                                    return json.loads(item["text"])
                                except:
                                    pass
                except:
                    pass

                # 如果无法进一步解析，返回result部分
                return raw_response["result"]
            else:
                # 返回整个响应
                return raw_response

        except json.JSONDecodeError as e:
            # 如果无法解析为JSON，返回原始文本
            return {"raw_text": stdout, "error": "无法解析为JSON"}

    except Exception as e:
        return {"error": str(e)}

    finally:
        # 清理资源
        if process and process.poll() is None:
            try:
                process.terminate()
            except:
                pass

if __name__ == "__main__":
    load_dotenv()
    mcp.run()