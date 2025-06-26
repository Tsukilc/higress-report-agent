"""
报告生成器 - 使用策略模式和工厂模式实现月报和changelog的生成

主要设计模式:
1. 策略模式: 不同类型报告使用不同的生成策略
2. 模板方法模式: 定义报告生成的基本流程
3. 工厂模式: 创建不同类型的报告生成器
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import os
from qwen_agent.agents import Assistant
from dataclasses import dataclass
from enum import Enum


class PRType(Enum):
    """PR类型枚举"""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    DOC = "doc"
    REFACTOR = "refactor"
    TEST = "test"


@dataclass
class PRInfo:
    """PR信息数据类"""
    number: int
    title: str
    html_url: str
    user: Dict[str, Any]
    highlight: str = ""
    function_value: str = ""
    score: int = 0
    pr_type: Optional[PRType] = None


class ReportGeneratorInterface(ABC):
    """报告生成器接口"""
    
    @abstractmethod
    def get_pr_list(self, **kwargs) -> List[PRInfo]:
        """获取PR列表 - 不同类型的报告有不同的获取方式"""
        pass
    
    @abstractmethod
    def analyze_prs_with_llm(self, pr_list: List[PRInfo]) -> List[PRInfo]:
        """使用LLM分析PR列表 - 通用逻辑"""
        pass
    
    @abstractmethod
    def generate_report(self, analyzed_prs: List[PRInfo]) -> str:
        """生成报告 - 不同类型的报告有不同的格式"""
        pass
    
    def create_report(self, **kwargs) -> str:
        """模板方法 - 定义报告生成的完整流程"""
        # 1. 获取PR列表
        pr_list = self.get_pr_list(**kwargs)
        
        # 2. 使用LLM分析PR
        analyzed_prs = self.analyze_prs_with_llm(pr_list)
        
        # 3. 生成报告
        report = self.generate_report(analyzed_prs)
        
        return report


class BaseReportGenerator(ReportGeneratorInterface):
    """报告生成器基类 - 实现通用逻辑"""
    
    def __init__(self):
        self.llm_assistant = self._create_llm_assistant()
    
    def _create_llm_assistant(self) -> Assistant:
        """创建LLM助手"""
        llm_cfg = {
            'model': os.getenv('MODEL_NAME'),
            'model_server': os.getenv('MODEL_SERVER'),
            'api_key': os.getenv('DASHSCOPE_API_KEY'),
        }
        return Assistant(llm=llm_cfg)
    
    def analyze_prs_with_llm(self, pr_list: List[PRInfo]) -> List[PRInfo]:
        """使用LLM分析PR列表 - 通用实现"""
        analyzed_prs = []
        
        for pr in pr_list:
            try:
                # 调用LLM分析单个PR
                analyzed_pr = self._analyze_single_pr(pr)
                analyzed_prs.append(analyzed_pr)
            except Exception as e:
                print(f"分析PR #{pr.number}时发生错误: {str(e)}")
                analyzed_prs.append(pr)  # 如果分析失败，使用原始PR
        
        return analyzed_prs
    
    def _analyze_single_pr(self, pr: PRInfo) -> PRInfo:
        """分析单个PR - 子类可以重写此方法来定制分析逻辑"""
        # 默认实现：如果已经有分析结果就直接返回
        if pr.highlight and pr.function_value:
            return pr
        
        # 否则使用基础分析，子类需要提供prompt
        prompt = self._get_analysis_prompt()
        return self._basic_pr_analysis(pr, prompt)
    
    def _get_analysis_prompt(self) -> str:
        """获取分析prompt - 子类必须重写此方法"""
        raise NotImplementedError("子类必须实现 _get_analysis_prompt 方法")
    
    def _basic_pr_analysis(self, pr: PRInfo, analysis_prompt: str) -> PRInfo:
        """基础PR分析 - 调用MCP工具获取PR详细信息并分析"""
        try:
            # 1. 获取PR的详细信息和文件变更
            pr_details = self._get_pr_detailed_info(pr.number)
            if not pr_details:
                print(f"无法获取PR #{pr.number}的详细信息")
                return pr
            
            # 2. 准备分析数据
            pr_info = {
                "number": pr.number,
                "title": pr.title,
                "body": pr_details.get("body", "")[:500] if pr_details.get("body") else "",
                "total_changes": pr_details.get("total_changes", 0),
                "file_changes": pr_details.get("file_changes", [])
            }
            
            # 3. 构建完整的分析请求
            full_prompt = analysis_prompt.format(
                pr_number=pr.number,
                pr_title=pr.title,
                pr_body=pr_info["body"],
                total_changes=pr_info["total_changes"],
                file_changes=json.dumps(pr_info["file_changes"][:5], indent=2, ensure_ascii=False)  # 限制文件数量
            )
            
            # 4. 使用LLM分析
            messages = [{'role': 'user', 'content': full_prompt}]
            response_text = self._get_llm_response(messages)
            
            # 5. 解析结果
            result = json.loads(response_text)
            pr.highlight = result.get("highlight", pr.highlight)
            pr.function_value = result.get("function_value", pr.function_value)
            
            # 6. 如果包含评分，解析评分（月报专用）
            if "score" in result:
                try:
                    pr.score = int(result.get("score", 0))
                except (ValueError, TypeError):
                    pr.score = 0
            
            # 7. 如果是changelog，还要解析类型
            if hasattr(self, '_parse_pr_type') and "pr_type" in result:
                pr.pr_type = self._parse_pr_type(result.get("pr_type", "feature"))
            
            print(f"PR #{pr.number}分析完成")
            
        except Exception as e:
            print(f"LLM分析PR #{pr.number}失败: {str(e)}")
            # 设置默认值
            pr.highlight = pr.highlight or "技术更新"
            pr.function_value = pr.function_value or "功能改进"
        
        return pr
    
    def _get_pr_detailed_info(self, pr_number: int) -> dict:
        """获取PR的详细信息，包括文件变更"""
        try:
            from utils.pr_helper import GitHubHelper
            github_helper = GitHubHelper()
            
            # 获取PR基本信息
            pr_info = github_helper.get_pull_request(
                owner="alibaba", 
                repo="higress", 
                pullNumber=pr_number
            )
            
            # 获取PR文件变更信息
            files_result = github_helper.get_pull_request_files(
                owner="alibaba", 
                repo="higress", 
                pullNumber=pr_number
            )
            
            if not isinstance(files_result, list):
                return {
                    "body": pr_info.get("body", "") if pr_info else "",
                    "total_changes": 0,
                    "file_changes": []
                }
                
            # 计算总变更行数
            total_changes = 0
            for file_info in files_result:
                total_changes += file_info.get("additions", 0) + file_info.get("deletions", 0)
            
            # 准备文件变更信息
            file_changes = [
                {
                    "filename": file.get("filename", ""),
                    "additions": file.get("additions", 0),
                    "deletions": file.get("deletions", 0),
                    "patch": file.get("patch", "")[:200] if file.get("patch") else ""  # 截取部分patch内容
                } for file in files_result[:10]  # 限制文件数量
            ]
            
            return {
                "body": pr_info.get("body", "") if pr_info else "",
                "total_changes": total_changes,
                "file_changes": file_changes
            }
            
        except Exception as e:
            print(f"获取PR #{pr_number}详细信息失败: {str(e)}")
            return {
                "body": "",
                "total_changes": 0,
                "file_changes": []
            }
    
    def _get_llm_response(self, messages: List[Dict[str, str]]) -> str:
        """获取LLM响应"""
        collected_responses = []
        for response in self.llm_assistant.run(messages=messages):
            if isinstance(response, list) and len(response) > 0:
                for msg in response:
                    if msg.get('role') == 'assistant' and msg.get('content'):
                        collected_responses.append(msg.get('content', ""))
        
        return collected_responses[-1] if collected_responses else ""


class ReportGeneratorFactory:
    """报告生成器工厂类"""
    
    @staticmethod
    def create_generator(report_type: str) -> ReportGeneratorInterface:
        """创建指定类型的报告生成器"""
        if report_type.lower() == "monthly":
            from monthly_report_generator import MonthlyReportGenerator
            return MonthlyReportGenerator()
        elif report_type.lower() == "changelog":
            from changelog_generator import ChangelogReportGenerator
            return ChangelogReportGenerator()
        else:
            raise ValueError(f"不支持的报告类型: {report_type}") 