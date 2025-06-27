"""
Issue操作辅助工具类 - 封装GitHub Issue相关的API调用
"""

import os
import subprocess
import json
from typing import Dict, Any, List, Optional


class IssueHelper:
    """Issue操作助手类"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not self.github_token:
            raise ValueError("Missing required environment variable GITHUB_PERSONAL_ACCESS_TOKEN")
    
    def get_good_first_issues(self, owner: str, repo: str, state: str = "open", 
                             labels: Optional[List[str]] = None, perPage: int = 2) -> List[Dict[str, Any]]:
        """
        获取新手友好的Issues
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: Issue状态
            labels: 标签过滤
            perPage: 每页数量
            
        Returns:
            Issue列表
        """
        if labels is None:
            labels = ["good first issue"]
        
        params = {
            "owner": owner,
            "repo": repo,
            "state": state,
            "labels": labels,
            "perPage": perPage
        }
        
        result = self._call_github_mcp_tool("list_issues", params)
        return result if isinstance(result, list) else []
    
    def list_issues(self, owner: str, repo: str, state: str = "open", 
                   labels: Optional[List[str]] = None, page: int = 1, 
                   perPage: int = 30) -> List[Dict[str, Any]]:
        """
        列出Issues
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: Issue状态
            labels: 标签过滤
            page: 页码
            perPage: 每页数量
            
        Returns:
            Issue列表
        """
        params = {
            "owner": owner,
            "repo": repo,
            "state": state,
            "page": page,
            "perPage": perPage
        }
        
        if labels:
            params["labels"] = labels
        
        result = self._call_github_mcp_tool("list_issues", params)
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
        if "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
            raise ValueError("缺少GITHUB_PERSONAL_ACCESS_TOKEN环境变量")

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
            # 启动进程 - 使用issues工具集
            process = subprocess.Popen(
                ["./github-mcp-serve", "stdio", "--toolsets", "issues"],
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