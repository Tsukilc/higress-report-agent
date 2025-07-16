"""
月报生成器 - 实现月报特有的PR获取和报告格式生成逻辑
"""
from datetime import timezone
from typing import List, Dict, Any
import datetime
from report_generator import BaseReportGenerator, PRInfo
from utils.pr_helper import GitHubHelper
from utils.issue_helper import IssueHelper


class MonthlyReportGenerator(BaseReportGenerator):
    """月报生成器"""
    
    def __init__(self):
        super().__init__()
        self.issue_helper = IssueHelper()
    
    def get_pr_list(self, **kwargs) -> List[PRInfo]:
        """获取月报的PR列表 - 独立实现月报PR获取逻辑"""
        owner = self.owner
        repo = self.repo
        month = kwargs.get('month')
        year = kwargs.get('year')
        per_page = kwargs.get('perPage', 100)
        important_pr_list = kwargs.get('important_pr_list', [])
        
        # 如果没有指定月份和年份，使用当前月份
        if not month or not year:
            current_date = datetime.datetime.now(timezone.utc)
            month = month or current_date.month
            year = year or current_date.year
        
        print(f"获取{year}年{month}月的PR列表...")
        if important_pr_list:
            print(f"重要PR列表: {important_pr_list}")
        
        # 获取合并的PR列表，按月份过滤
        pr_list = []
        page = 1
        # 魔数，一般20页就扫完了
        max_pages = 20
        
        while page <= max_pages:
            print(f"正在获取第{page}页PR数据...")
            
            # 获取已合并的PR
            prs_data = self.github_helper.list_pull_requests(
                owner=owner,
                repo=repo,
                state="closed",
                page=page,
                perPage=per_page
            )
            
            if not prs_data:
                break
            
            # 按月份过滤PR
            filtered_prs = self._filter_prs_by_month(prs_data, month, year)
            
            # 转换为PRInfo对象
            for pr_data in filtered_prs:
                # 只处理已合并的PR
                if not pr_data.get("merged_at"):
                    continue
                    
                # 跳过草稿PR
                if pr_data.get("draft", False):
                    continue
                
                pr_number = pr_data.get('number', 0)
                pr_info = self._create_pr_info(pr_data, is_important=pr_number in important_pr_list)
                pr_list.append(pr_info)
            
            # 检查是否还需要继续获取
            if filtered_prs:
                last_pr = filtered_prs[-1]
                last_pr_year, last_pr_month = GitHubHelper.extract_year_month_from_date(
                    last_pr.get("merged_at", "")
                )
                # 如果最后一个PR的日期早于目标月份，停止获取
                if (last_pr_year and last_pr_month and 
                    (last_pr_year < year or (last_pr_year == year and last_pr_month < month))):
                    break
            
            page += 1
        
        # 检查是否有重要PR不在月份范围内，如果有则单独获取
        if important_pr_list:
            existing_pr_numbers = {pr.number for pr in pr_list}
            missing_important_prs = [pr_num for pr_num in important_pr_list if pr_num not in existing_pr_numbers]
            
            if missing_important_prs:
                print(f"发现{len(missing_important_prs)}个重要PR不在当月范围内，单独获取: {missing_important_prs}")
                for pr_num in missing_important_prs:
                    try:
                        pr_data = self.github_helper.get_pull_request(
                            owner=owner,
                            repo=repo,
                            pullNumber=pr_num
                        )
                        
                        if pr_data and pr_data.get("merged_at"):
                            pr_info = self._create_pr_info(pr_data, is_important=True)
                            pr_list.append(pr_info)
                            print(f"✅ 已添加重要PR #{pr_num}")
                    except Exception as e:
                        print(f"❌ 获取重要PR #{pr_num}失败: {str(e)}")
        
        important_count = len([pr for pr in pr_list if pr.is_important])
        print(f"成功获取{len(pr_list)}个PR（其中{important_count}个重要PR），准备进行质量评估...")
        return pr_list
    
    def _get_analysis_prompt(self) -> str:
        """获取月报专用的分析prompt"""
        return """
        你是一个优秀的月报生成专家，请根据以下标准对PR进行分析和评分（总分129分）：

        附加提示（优先参考，作为判断PR性质和评分的标准）：
        - 文档类PR：标题通常带有md、文档、docs、readme、description等，这样的PR归类于文档类PR，总评分30分以下
        - 功能性PR：标题开头带有feat、optimize、support、增强等，可以归类功能性PR
        - 修复性PR：标题开头带有fix、修复、bug等
        - 测试类PR：title带有test、e2e等，总评分只能40分以下

        评分标准：
        1. 技术复杂度（50分）：
           - 高（40-50分）：涉及核心架构变更、重要算法实现、跨组件重构、新功能实现
           - 中（20-39分）：功能增强、复杂的Bug修复
           - 低（1-19分）：简单Bug修复、配置修改、文档类PR、bot发布的PR、测试类PR

        2. 用户影响范围（40分）：
           - 高（30-40分）：影响所有用户、核心功能改进、新增重要特性
           - 中（15-29分）：影响部分用户、功能增强、可用性改进
           - 低（1-14分）：影响少数用户、次要功能修复、内部改进、测试类PR

        3. 代码量与复杂度（30分）：
           - 代码行数变化很小的PR（<10行）不能作为亮点功能，直接排除
           - 文档类PR直接排除，不计分
           - 代码行数10-100行的PR，最高只能得到25分
           - 代码行数100行以上且复杂度高的PR，获得25-30分

        4. Bug重要性（9分）：
           - 高（7-9分）：修复严重影响用户体验或系统稳定性的Bug
           - 中（4-6分）：修复中等影响的Bug
           - 低（1-3分）：修复轻微问题或边缘情况

        请分析以下PR（需要根据文件改动、PR描述和社区评论进行具体分析）：
        PR编号: #{pr_number}
        PR标题: {pr_title}
        PR描述: {pr_body}
        总变更行数: {total_changes}
        文件变更详情:
        {file_changes}
        
        社区评论摘要:
        {comments_summary}

        请严格按照以下JSON格式返回，不要添加任何解释、语言标记、代码块符号（如 ```json）：
        {{
            "highlight": "关键技术实现方式和原理(50字以上，100字以下)",
            "function_value": "功能价值概要，对社区的影响(50字以上，100字以下)",
            "score": "你给出的整数评分（1-129）"
        }}
        """
    
    def analyze_prs_with_llm(self, pr_list: List[PRInfo]) -> List[PRInfo]:
        """月报的LLM分析 - 包含评分和筛选逻辑，支持重要PR详细分析"""
        analyzed_prs = []
        
        print(f"开始分析{len(pr_list)}个PR...")
        
        for i, pr in enumerate(pr_list):
            try:
                print(f"正在分析PR #{pr.number}: {pr.title} ({i+1}/{len(pr_list)})")
                
                # 根据PR是否标记为重要来选择分析方法
                if pr.is_important:
                    # 重要PR使用详细分析
                    analyzed_pr = self._analyze_important_pr(pr)
                else:
                    # 普通PR使用基础分析
                    analyzed_pr = self._analyze_single_pr(pr)
                
                # 提取评分（如果LLM返回了评分）
                if hasattr(analyzed_pr, 'score') and analyzed_pr.score:
                    analyzed_prs.append(analyzed_pr)
                else:
                    # 如果没有评分，给一个默认评分
                    analyzed_pr.score = 50
                    analyzed_prs.append(analyzed_pr)
                    
            except Exception as e:
                print(f"分析PR #{pr.number}时发生错误: {str(e)}")
                pr.highlight = pr.highlight or "技术更新"
                pr.function_value = pr.function_value or "功能改进"
                pr.score = 30  # 默认评分
                analyzed_prs.append(pr)
        
        # 按评分降序排序
        analyzed_prs.sort(key=lambda x: x.score, reverse=True)
        
        # 获取配置的优质PR数量
        import os
        good_pr_num = int(os.getenv("GOOD_PR_NUM", "10"))
        top_prs = analyzed_prs[:good_pr_num]
        
        print(f"分析完成，从{len(analyzed_prs)}个PR中选出评分最高的{len(top_prs)}个")
        return top_prs
    
    def generate_report(self, analyzed_prs: List[PRInfo]) -> str:
        """生成月报格式的报告"""
        # 生成报告头部
        report = "# higress社区月报\n\n"
        
        # 添加good first issue部分
        good_first_issues = self._get_good_first_issues()
        if good_first_issues:
            report += "## ⚙️good first issue\n"
            for issue in good_first_issues:
                report += f"### {issue['title']}\n"
                report += f"- 相关issue：{issue['html_url']}\n"
                report += f"- issue概要：{issue.get('body', '')[:100]}...\n\n"
        
        # 分离重要PR和普通PR
        important_prs = [pr for pr in analyzed_prs if pr.is_important]
        normal_prs = [pr for pr in analyzed_prs if not pr.is_important]
        
        # 添加重要功能详述部分（如果有重要PR）
        if important_prs:
            report += "## 🌟 本月重要功能详述\n\n"
            for i, pr in enumerate(important_prs, 1):
                function_name = self._extract_function_name(pr.title)
                contributor_login = pr.user.get('login', '未知')
                contributor_url = pr.user.get('html_url', '#')
                
                report += f"### {i}. {function_name}\n\n"
                report += f"**相关PR**: [#{pr.number}]({pr.html_url}) | "
                report += f"**贡献者**: [{contributor_login}]({contributor_url})\n\n"
                
                if pr.detailed_analysis:
                    # 使用详细分析内容
                    report += f"{pr.detailed_analysis}\n\n"
                else:
                    # 降级为基础信息
                    report += f"**技术看点**: {pr.highlight}\n\n"
                    report += f"**功能价值**: {pr.function_value}\n\n"
                
                report += "---\n\n"
        
        # 添加本月亮点功能部分（普通PR）
        if normal_prs:
            report += "## 📌本月亮点功能\n"
            for pr in normal_prs:
                # 提取功能名称（从标题中提取关键词）
                function_name = self._extract_function_name(pr.title)
                
                report += f"### {function_name}\n"
                report += f"- 相关pr：{pr.html_url}\n"
                
                # 处理贡献者信息
                contributor_login = pr.user.get('login', '未知')
                contributor_url = pr.user.get('html_url', '#')
                report += f"- 贡献者：[{contributor_login}]({contributor_url})\n"
                
                report += f"- 技术看点：{pr.highlight}\n"
                report += f"- 功能价值：{pr.function_value}\n\n"
        
        # 添加结语
        report += "## 结语\n"
        report += f"- 本月Higress社区持续活跃发展，共有{len(analyzed_prs)}个重要功能更新和改进\n"
        report += "- 感谢所有贡献者的辛勤付出，欢迎更多开发者加入Higress社区贡献\n"
        report += "- higress社区github地址: https://github.com/alibaba/higress\n"
        
        return report
    
    def _get_good_first_issues(self) -> List[Dict[str, Any]]:
        """获取新手友好的Issues"""
        try:
            issues = self.issue_helper.get_good_first_issues(
                owner=self.owner,
                repo=self.repo,
                state='open',
                labels=['good first issue'],
                perPage=2
            )
            return issues
        except Exception as e:
            print(f"获取good first issue失败: {str(e)}")
            return []
    
    def _get_detailed_analysis_prompt(self) -> str:
        """获取重要PR的详细分析prompt（月报专用版本）"""
        return """
        你是一个专业的技术文档撰写专家，请对以下重要PR进行深度分析，为月报撰写详细的功能介绍。

        你将获得完整的代码变更信息（包括patch内容）和社区评论，请基于这些具体信息进行权威分析。

        请从以下几个维度进行详细分析：

        1. **使用背景**: 
           - 解决了什么问题或满足了什么需求
           - 为什么需要这个功能/修复
           - 目标用户群体

        2. **功能详述**:
           - 具体实现了什么功能
           - 核心技术要点和创新之处
           - 与现有功能的关系和差异
           - 基于代码变更的技术分析

        3. **使用方式**:
           - 如何启用和配置这个功能
           - 典型的使用场景和示例
           - 注意事项和最佳实践

        4. **功能价值**:
           - 为用户带来的具体好处
           - 对系统性能、稳定性、易用性的提升
           - 对社区发展的意义

        请分析以下重要PR：
        PR编号: #{pr_number}
        PR标题: {pr_title}
        PR描述: {pr_body}
        总变更行数: {total_changes}
        
        主要文件变更:
        {file_changes}
        
        关键代码变更摘要:
        {patch_summary}
        
        社区评论摘要:
        {comments_summary}

        请基于具体的代码变更内容和社区反馈进行分析，严格按照以下JSON格式返回：
        {{
            "highlight": "关键技术实现方式和原理(50字以上，100字以下)",
            "function_value": "功能价值概要，对社区的影响(50字以上，100字以下)",
            "score": "你给出的整数评分（1-129）",
            "usage_background": "使用背景详述(200-400字)",
            "feature_details": "功能详述，包含技术实现分析(200-400字)", 
            "usage_guide": "使用方式详述(200-400字)",
            "value_proposition": "功能价值详述(200-400字)"
        }}
        """
    
    def _extract_function_name(self, title: str) -> str:
        """从PR标题中提取功能名称"""
        # 简单的功能名称提取逻辑
        # 移除常见的前缀
        cleaned_title = title
        prefixes = ['feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:']
        for prefix in prefixes:
            if cleaned_title.lower().startswith(prefix):
                cleaned_title = cleaned_title[len(prefix):].strip()
                break
        
        # 如果标题太长，取前30个字符
        if len(cleaned_title) > 30:
            cleaned_title = cleaned_title[:30] + "..."
        
        return cleaned_title or "功能更新"
    

    def _filter_prs_by_month(self, prs_data: List[Dict[str, Any]], month: int, year: int) -> List[Dict[str, Any]]:
        """根据年份和月份过滤PR列表"""
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
    
 