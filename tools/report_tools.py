"""
报告生成工具 - MCP工具类
"""
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from report_generator import ReportGeneratorFactory


@register_tool('generate_monthly_report_mcp')
class GenerateMonthlyReport(BaseTool):
    description = '只有生成完整月报时要调用，用于生成指定月份的项目月报，包含PR统计、贡献者信息等。不具备修改月报功能'
    parameters = [
        {
            'name': 'month',
            'type': 'integer',
            'description': '月份，1-12之间的整数，默认当前月',
            'required': True
        },
        {
            'name': 'year',
            'type': 'integer',
            'description': '年份，4位数字，默认当前年',
            'required': True
        },
        {
            'name': 'important_pr_list',
            'type': 'array',
            'description': '重要PR编号列表，数组格式',
            'required': True
        },
        {
            'name': 'owner',
            'type': 'string',
            'description': '仓库所有者，如alibaba',
            'required': True
        },
        {
            'name': 'repo',
            'type': 'string',
            'description': '仓库名称，如higress',
            'required': True
        },
        {
            'name': 'translate',
            'type': 'boolean',
            'description': '是否生成英文翻译，true为生成，false为不生成',
            'required': True
        }
    ]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        if isinstance(params, str):
            params = json.loads(params)

        print("🚀 开始生成月报...")

        try:
            # 使用工厂模式创建月报生成器
            generator = ReportGeneratorFactory.create_generator("monthly")

            # 准备参数
            kwargs = {
                'month': params.get('month'),
                'year': params.get('year'),
                'owner': params.get('owner'),
                'repo': params.get('repo'),
                'translate': params.get('translate', True)
            }

            # 如果有重要PR列表，添加到参数中
            if params.get('important_pr_list'):
                kwargs['important_pr_list'] = params['important_pr_list']

            # 生成月报
            report = generator.create_report(**kwargs)

            print("✅ 月报生成完成!")
            return report

        except Exception as e:
            print(f"❌ 月报生成失败: {str(e)}")
            return f"月报生成失败: {str(e)}"


@register_tool('generate_changelog_mcp')
class GenerateChangelog(BaseTool):
    description = '生成changelog工具，用于根据PR列表生成版本更新日志。不具备修改 changelog 的功能'
    parameters = [
        {
            'name': 'pr_num_list',
            'type': 'array',
            'description': 'PR编号列表，必填参数',
            'required': True
        },
        {
            'name': 'important_pr_list',
            'type': 'array',
            'description': '重要PR编号列表，数组格式',
            'required': True
        },
        {
            'name': 'owner',
            'type': 'string',
            'description': '仓库所有者，如alibaba',
            'required': True
        },
        {
            'name': 'repo',
            'type': 'string',
            'description': '仓库名称，如higress',
            'required': True
        },
        {
            'name': 'translate',
            'type': 'boolean',
            'description': '是否生成英文翻译，true为生成，false为不生成',
            'required': True
        }
    ]

    def call(self, params: Union[str, dict], **kwargs) -> str:
        if isinstance(params, str):
            params = json.loads(params)

        print("🚀 开始生成changelog...")

        try:
            # 使用工厂模式创建changelog生成器
            generator = ReportGeneratorFactory.create_generator("changelog")

            # 准备参数
            kwargs = {
                'pr_num_list': params['pr_num_list'],
                'owner': params.get('owner'),
                'repo': params.get('repo'),
                'translate': params.get('translate', True)
            }

            # 如果有重要PR列表，添加到参数中
            if params.get('important_pr_list'):
                kwargs['important_pr_list'] = params['important_pr_list']

            # 生成changelog
            report = generator.create_report(**kwargs)

            print("✅ Changelog生成完成!")
            return report

        except Exception as e:
            print(f"❌ Changelog生成失败: {str(e)}")
            return f"Changelog生成失败: {str(e)}"
