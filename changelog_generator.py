"""
Changelog生成器 - 实现changelog特有的PR获取和报告格式生成逻辑
"""

from typing import List, Dict, Any
import json
from collections import defaultdict
from report_generator import BaseReportGenerator, PRInfo, PRType
from utils.pr_helper import GitHubHelper


class ChangelogReportGenerator(BaseReportGenerator):
    """Changelog生成器"""
    
    def __init__(self):
        super().__init__()
        self.github_helper = GitHubHelper()
        self._setup_changelog_llm()
    
    def _setup_changelog_llm(self):
        """设置changelog专用的LLM系统指令"""
        changelog_system = """
        你是一个专业的PR分类和分析助手，负责分析GitHub PR并为changelog生成分类信息。

        请根据以下标准对PR进行分析：

        1. PR类型分类：
           - feature: 新功能、功能增强、新特性
           - bugfix: Bug修复、问题解决
           - doc: 文档更新、文档修复
           - refactor: 代码重构、性能优化、代码清理
           - test: 测试相关、CI/CD改进

        2. 分析要求：
           - 技术看点：关键技术实现方式和原理(50字以内)
           - 功能价值：功能价值概要，对用户的影响(50字以内)

        请严格按照以下JSON格式返回：
        {
            "pr_type": "feature|bugfix|doc|refactor|test",
            "highlight": "关键技术实现方式和原理(50字以内)",
            "function_value": "功能价值概要，对用户的影响(50字以内)"
        }
        """
        
        self.changelog_llm = self._create_llm_assistant()
        self.changelog_llm.system_message = changelog_system
    
    def get_pr_list(self, **kwargs) -> List[PRInfo]:
        """获取changelog的PR列表 - 根据pr_num_list获取"""
        pr_num_list = kwargs.get('pr_num_list', [])
        owner = kwargs.get('owner', 'alibaba')
        repo = kwargs.get('repo', 'higress')
        
        if not pr_num_list:
            print("警告: 没有提供PR编号列表")
            return []
        
        print(f"开始获取{len(pr_num_list)}个指定PR的详细信息...")
        
        pr_list = []
        for pr_number in pr_num_list:
            try:
                # 调用get_pull_request MCP工具获取单个PR信息
                pr_data = self.github_helper.get_pull_request(
                    owner=owner,
                    repo=repo,
                    pullNumber=pr_number
                )
                
                if pr_data:
                    pr_info = PRInfo(
                        number=pr_data.get('number', pr_number),
                        title=pr_data.get('title', ''),
                        html_url=pr_data.get('html_url', ''),
                        user=pr_data.get('user', {}),
                        highlight='',  # 待LLM分析
                        function_value='',  # 待LLM分析
                        score=0
                    )
                    pr_list.append(pr_info)
                    print(f"✓ 成功获取PR #{pr_number}: {pr_info.title}")
                else:
                    print(f"✗ 获取PR #{pr_number}失败")
                    
            except Exception as e:
                print(f"✗ 获取PR #{pr_number}时发生错误: {str(e)}")
                continue
        
        print(f"成功获取{len(pr_list)}个PR的详细信息")
        return pr_list
    
    def _get_analysis_prompt(self) -> str:
        """获取changelog专用的分析prompt"""
        return """
        你是一个专业的PR分类和分析助手，负责分析GitHub PR并为changelog生成分类信息。

        请根据以下标准对PR进行分析：

        1. PR类型分类：
           - feature: 新功能、功能增强、新特性（标题包含feat、add、support、implement、enhance等）
           - bugfix: Bug修复、问题解决（标题包含fix、resolve、correct、patch等）
           - doc: 文档更新、文档修复（标题包含doc、readme、documentation、guide等）
           - refactor: 代码重构、性能优化、代码清理（标题包含refactor、optimize、improve、clean等）
           - test: 测试相关、CI/CD改进（标题包含test、ci、cd、workflow等）

        2. 分析要求：
           - 技术看点：关键技术实现方式和原理(50字以内)
           - 功能价值：功能价值概要，对用户的影响(50字以内)

        请分析以下PR：
        PR编号: #{pr_number}
        PR标题: {pr_title}
        PR描述: {pr_body}
        总变更行数: {total_changes}
        文件变更详情:
        {file_changes}

        请严格按照以下JSON格式返回：
        {{
            "pr_type": "feature|bugfix|doc|refactor|test",
            "highlight": "pr做了哪些变更(50字以内)",
            "function_value": "功能价值概要，对用户的影响(50字以内)"
        }}
        """
    
    def _parse_pr_type(self, pr_type_str: str) -> PRType:
        """解析PR类型字符串为枚举"""
        type_mapping = {
            'feature': PRType.FEATURE,
            'bugfix': PRType.BUGFIX,
            'doc': PRType.DOC,
            'refactor': PRType.REFACTOR,
            'test': PRType.TEST
        }
        return type_mapping.get(pr_type_str.lower(), PRType.FEATURE)
    
    def generate_report(self, analyzed_prs: List[PRInfo]) -> str:
        """生成changelog格式的报告"""
        # 按类型分组PR
        grouped_prs = self._group_prs_by_type(analyzed_prs)
        
        # 生成报告
        report = "# Changelog\n\n"
        
        # 定义类型顺序和标题
        type_order = [
            (PRType.FEATURE, "## 🚀 新功能 (Features)"),
            (PRType.BUGFIX, "## 🐛 Bug修复 (Bug Fixes)"),
            (PRType.REFACTOR, "## ♻️ 重构优化 (Refactoring)"),
            (PRType.DOC, "## 📚 文档更新 (Documentation)"),
            (PRType.TEST, "## 🧪 测试改进 (Testing)")
        ]
        
        for pr_type, type_title in type_order:
            prs = grouped_prs.get(pr_type, [])
            if prs:
                report += f"{type_title}\n\n"
                
                for pr in prs:
                    # 生成PR条目
                    contributor_login = pr.user.get('login', '未知')
                    contributor_url = pr.user.get('html_url', '#')
                    
                    report += f"### {pr.title}\n"
                    report += f"- **Related PR:**: [#{pr.number}]({pr.html_url})\n"
                    report += f"- **Contributor**: [{contributor_login}]({contributor_url})\n"
                    report += f"- **Change Log**: {pr.highlight}\n"
                    report += f"- **Feature Value**: {pr.function_value}\n\n"
        
        # 添加统计信息
        total_count = len(analyzed_prs)
        report += "---\n\n"
        report += "## 📊 本次更新统计\n\n"
        
        for pr_type, type_title in type_order:
            count = len(grouped_prs.get(pr_type, []))
            if count > 0:
                type_name = type_title.split('(')[0].replace('##', '').strip()
                report += f"- {type_name}: {count}个\n"
        
        report += f"\n**总计**: {total_count}个更改\n\n"
        report += "感谢所有贡献者的辛勤付出！🎉\n"
        
        return report
    
    def _group_prs_by_type(self, prs: List[PRInfo]) -> Dict[PRType, List[PRInfo]]:
        """按类型分组PR"""
        grouped = defaultdict(list)
        
        for pr in prs:
            pr_type = pr.pr_type or PRType.FEATURE
            grouped[pr_type].append(pr)
        
        # 对每个类型内的PR按编号排序
        for pr_type in grouped:
            grouped[pr_type].sort(key=lambda x: x.number, reverse=True)
        
        return dict(grouped) 