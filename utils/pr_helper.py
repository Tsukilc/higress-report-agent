"""
PR操作辅助工具类 - 封装GitHub PR相关的API调用
"""

import os
import subprocess
import json
import datetime
import re
from typing import Dict, Any, List, Optional
from dateutil import parser as date_parser


class GitHubHelper:
    """GitHub操作助手类"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not self.github_token:
            raise ValueError("Missing required environment variable GITHUB_PERSONAL_ACCESS_TOKEN")

    
    def get_pull_request(self, owner: str, repo: str, pullNumber: int) -> Optional[Dict[str, Any]]:
        """
        获取单个PR的详细信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pullNumber: PR编号
            
        Returns:
            PR详细信息字典，失败返回None
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pullNumber": pullNumber
        }
        
        return self._call_github_mcp_tool("get_pull_request", params)
    
    def list_pull_requests(self, owner: str, repo: str, state: str = "closed", 
                          page: int = 1, perPage: int = 50) -> List[Dict[str, Any]]:
        """
        列出PR请求
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: PR状态
            page: 页码
            perPage: 每页数量
            
        Returns:
            PR列表
        """
        params = {
            "owner": owner,
            "repo": repo,
            "state": state,
            "page": page,
            "perPage": perPage
        }
        
        result = self._call_github_mcp_tool("list_pull_requests", params)
        return result if isinstance(result, list) else []
    
    def get_pull_request_files(self, owner: str, repo: str, pullNumber: int) -> List[Dict[str, Any]]:
        """
        获取PR的文件变更信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pullNumber: PR编号
            
        Returns:
            文件变更列表
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pullNumber": pullNumber
        }
        
        result = self._call_github_mcp_tool("get_pull_request_files", params)
        return result if isinstance(result, list) else []
    
    def get_pull_request_comments(self, owner: str, repo: str, pullNumber: int) -> List[Dict[str, Any]]:
        """
        获取PR的评论信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pullNumber: PR编号
            
        Returns:
            评论列表
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pullNumber": pullNumber
        }
        
        result = self._call_github_mcp_tool("get_pull_request_comments", params)
        return result if isinstance(result, list) else []
    
    def _call_github_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
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

        # 构建JSON-RPC请求
        request = {
            "jsonrpc": "2.0",
            "id": 1,
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
                print(f"GitHub MCP工具调用失败: {stderr}")
                return None

            try:
                # 解析响应
                raw_response = json.loads(stdout)
                
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
                    
                    return raw_response["result"]
                else:
                    return raw_response

            except json.JSONDecodeError:
                print(f"无法解析GitHub MCP工具响应: {stdout}")
                return None

        except Exception as e:
            print(f"调用GitHub MCP工具时发生错误: {str(e)}")
            return None

        finally:
            # 清理资源
            if 'process' in locals() and process.poll() is None:
                try:
                    process.terminate()
                except:
                    pass
    
    @staticmethod
    def extract_year_month_from_date(date_str: str) -> tuple[Optional[int], Optional[int]]:
        """
        从日期字符串中安全地提取年份和月份
        
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
    
    @staticmethod
    def filter_prs_by_year_month(prs_data: List[Dict[str, Any]], month: int, year: int) -> List[Dict[str, Any]]:
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

            pr_year, pr_month = GitHubHelper.extract_year_month_from_date(merged_at)
            if pr_year is not None and pr_month is not None and pr_year == year and pr_month == month:
                filtered_prs.append(pr)

        return filtered_prs
    
    @staticmethod
    def remove_unwanted_urls(data: Any) -> Any:
        """
        递归移除数据中不需要的URL字段
        
        Args:
            data: 要处理的数据(字典或列表)
            
        Returns:
            处理后的数据
        """
        if isinstance(data, dict):
            result = {}
            for key, value in list(data.items()):
                # 跳过以_url结尾且不是html_url的键
                if key.endswith("_url") and key != "html_url":
                    continue

                # 递归处理嵌套数据
                if isinstance(value, (dict, list)):
                    result[key] = GitHubHelper.remove_unwanted_urls(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [GitHubHelper.remove_unwanted_urls(item) for item in data]
        else:
            return data 