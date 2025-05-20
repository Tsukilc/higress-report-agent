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
from os import getenv

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


def extract_year_month_from_date(date_str):
    """
    从日期字符串中安全地提取年份和月份
    支持多种日期格式

    Args:
        date_str: 日期字符串

    Returns:
        (year, month)元组，解析失败返回(None, None)
    """
    if not date_str:
        return None, None

    try:
        # 方法1: ISO格式
        try:
            if 'T' in date_str and (date_str.endswith('Z') or '+' in date_str):
                dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.year, dt.month
        except ValueError:
            pass

        # 正则匹配
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            if 1 <= month <= 12:
                return year, month

        # 方法3: dateutil
        dt = date_parser.parse(date_str)
        return dt.year, dt.month

    except Exception:
        return None, None


def filter_prs_by_year_month(prs_data, month, year):
    """
    根据年份和月份过滤PR列表

    Args:
        prs_data: PR数据列表
        month: 目标月份(1-12)
        year: 目标年份

    Returns:
        过滤后的PR列表
    """
    if not month or not year or not isinstance(prs_data, list):
        return prs_data

    filtered_prs = []

    for pr in prs_data:
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        pr_year, pr_month = extract_year_month_from_date(merged_at)
        if pr_year is not None and pr_month is not None and pr_year == year and pr_month == month:
            filtered_prs.append(pr)

    return filtered_prs


@mcp.tool()
def get_current_year_month(
) -> Dict:
    """
    获取当前的年份和月份，仅当用户未输入当年年月时调用

    Returns:
        包含当前年份和月份的字典
    """
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month

    return {"year": year, "month": month}



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
        year: Optional[int] = None,  # 可选，按合并PR的年份过滤
        page: Optional[int] = 1,  # 可选，页码
        perPage: Optional[int] = 50  # 可选，每页结果数，默认增加到50以获取更多数据
) -> str | dict[str, list[dict] | int]:
    """
    增强版列出GitHub仓库中的PR请求，可以筛选出合并的请求和指定月份的请求，并进行评分筛选。
    此处返回的pr已经处理好，一共有total_count个，必须全部提取展示

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

    # 取评分最高的前n个
    size = int(getenv("GOOD_PR_NUM"))
    if size is None or size < 0:
        return "请指定大于0的亮点pr数量"


    pr_list = []
    # 尝试获取足够的PR数据
    tool_name = "list_pull_requests"
    page = 1
    maxPage = 20

    while(page<maxPage):
        # 先获取第一页
        print(f"获取PR第{page} 页数据...")
        params["page"] = page
        result = call_github_mcp_tool(tool_name, params)
        page_pr_list = filter_prs_by_year_month(result, month, year)
        pr_list.extend(page_pr_list)
        page+=1
        
        # 检查是否需要继续获取更多页数据
        # 如果当前页为空则停止获取
        if not result:
            break
            
        # 检查最后一个PR的日期
        last_pr = result[-1]
        if last_pr and "merged_at" in last_pr:
            last_pr_year, last_pr_month = extract_year_month_from_date(last_pr["merged_at"])
            if last_pr_year is not None and last_pr_month is not None:
                if last_pr_year < year or (last_pr_year == year and last_pr_month < month):
                    break

    scored_prs = []

    # 遍历page_pr_list打印年月
    for pr in pr_list:
        merged_at = pr.get("merged_at")
        if merged_at:
            pr_year, pr_month = extract_year_month_from_date(merged_at)
            print(f"PR #{pr.get('number')} 合并日期: {pr_year}-{pr_month}")

    # 导入必要的模块
    from qwen_agent.agents import Assistant

    # 创建一个专门用于PR评分的助手
    scoring_system = """
    你是一个专业的PR评价助手，严格根据以下标准，逐步骤对PR进行评分（总分129分），并且严格按照下文指定json格式返回：

    0. 附加提示(优先参考，作为判断pr性质和评分的标准)：
    文档类pr:标题通常带有md，文档，docs，readme，description，文档等，这样的pr归类于文档类pr，不用进行下面的过程，总评分30分以下
    功能性pr：标题开头带有 feat,optimize，support,增强，可以归类功能性pr
    修复性pr: 标题开头带有fix，修复，bug
    测试类pr: title带有text,e2e, 总评分只能40分以下，不用进行下面过程

    1. 技术复杂度 (50分)：
       - 高 (40-50分)：涉及核心架构变更、重要算法实现、跨组件重构、新功能实现
       - 中 (20-39分)：功能增强、复杂的Bug修复
       - 低 (1-19分)：简单Bug修复、配置修改，文档类pr，bot发布的pr，测试类pr

    2. 用户影响范围 (40分)：
       - 高 (30-40分)：影响所有用户、核心功能改进、新增重要特性
       - 中 (15-29分)：影响部分用户、功能增强、可用性改进
       - 低 (1-14分)：影响少数用户、次要功能修复、内部改进,测试类pr

    3. 代码量与复杂度 (30分)：
       - 代码行数变化很小的PR (<10行) 不能作为亮点功能，直接排除
       - 文档类PR直接排除，不计分
       - 代码行数10-100行的PR，最高只能得到25分
       - 代码行数100行以上且复杂度高的PR，获得25-30分

    4. Bug重要性 (9分)：
       - 高 (7-9分)：修复严重影响用户体验或系统稳定性的Bug
       - 中 (4-6分)：修复中等影响的Bug
       - 低 (1-3分)：修复轻微问题或边缘情况

    请根据以上标准对PR进行评分，并给出一个1-129之间的整数分数，严格注意测试和文档pr得分不超过40，严格参考评分标准。
    
    最后，请务必返回以下信息（填充具体值），严格按照json格式：
    "pr_link": ,
    "contributor": ,
    "highlight": "关键技术实现方式和原理(50字)",
    "function_value": "功能价值概要，对社区的影响(50字)"
    "score": "你给出的整数评分"
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
        pr_title = pr.get("title")
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
                
            print(f"PR #{pr_number} +{pr_title}总变更行数: {total_changes}")
            
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
                        "patch": file.get("patch", ""),
                        "filename": file.get("filename", ""),
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    } for file in files_result[:45]  # 限制文件数量，避免超出上下文长度
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

            collected_responses = []
            for response in scoring_bot.run(messages=messages):
                if isinstance(response, list) and len(response) > 0:
                    for msg in response:
                        if msg.get('role') == 'assistant' and msg.get('content'):
                            collected_responses.append(msg.get('content', ""))

            # 只取最后一个响应（完整响应）
            if collected_responses:
                response_text = collected_responses[-1]

            import re
            json_response = json.loads(response_text)

            score = json_response.get("score", 0)

            scored_pr = {
                "number": pr_number,
                "title": pr.get("title", ""),
                "html_url": pr.get("html_url", ""),
                "user": remove_unwanted_urls(pr.get("user", {})),
                "highlight": json_response.get("highlight", ""),
                "function_value": json_response.get("function_value", ""),
                "score": score
            }

            print(f"PR #{pr_number}评分完成，得分: {score}")
            print(scored_pr)

            scored_prs.append(scored_pr)
            
        except Exception as e:
            print(f"处理PR #{pr_number}时发生错误: {str(e)}")
            continue
    
    # 按评分降序排序
    scored_prs.sort(key=lambda x: x["score"], reverse=True)

    top_prs = scored_prs[:size]
    
    print(f"评分完成，共有{len(scored_prs)}个优秀PR，选出前{len(top_prs)}个")


    return {
        "total_count": len(scored_prs),
        "items": scored_prs
    }

def call_github_mcp_tool(tool_name: str, params: Dict[str, Any]) -> dict[str, str] | None:
    """
    调用GitHub MCP工具

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

