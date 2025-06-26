"""
报告生成主程序 - 使用重构后的报告生成器系统
"""

import os
from dotenv import load_dotenv
from qwen_agent.agents import Assistant
from qwen_agent.utils.output_beautify import typewriter_print
from report_generator import ReportGeneratorFactory


class ReportAgent:
    """报告生成代理类 - 封装LLM Agent和报告生成器的交互逻辑"""
    
    def __init__(self):
        self.llm_assistant = self._init_agent_service()
    
    def _init_agent_service(self):
        """初始化LLM Agent服务"""
        # LLM配置
        llm_cfg = {
            'model': os.getenv('MODEL_NAME'),
            'model_server': os.getenv('MODEL_SERVER'),
            'api_key': os.getenv('DASHSCOPE_API_KEY'),
            'generate_cfg': {
                'extra_body': {
                    'enable_thinking': False
                },
            },
        }
        
        # MCP工具配置
        tools = [
            {
                'mcpServers': {
                    'github-mcp-serve': {
                        'command': './github-mcp-serve',
                        "args": ["stdio", "--toolsets", "issues", "--toolsets", "pull_requests", "--toolsets", "repos"],
                        "env": {
                            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                        }
                    },
                    'github-mcp-server-proxy': {
                        "command": "uv",
                        "args": ['run', './github_proxy_mcp_server.py', "stdio", "--toolsets", "issues", "--toolsets", "pull_requests", "--toolsets", "repos"],
                        "env": {
                            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                        }
                    }
                }
            },
        ]

        # 验证GitHub token
        github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("Missing required environment variable GITHUB_PERSONAL_ACCESS_TOKEN")

        # 创建Agent
        bot = Assistant(
            llm=llm_cfg,
            function_list=tools,
            name='higress-report-agent',
            description="我是Higress社区报告生成助手，可以生成月报和changelog！"
        )

        return bot
    
    def generate_monthly_report(self, month: int = None, year: int = None, owner: str = "alibaba", repo: str = "higress") -> str:
        """
        生成月报
        
        Args:
            month: 月份，默认当前月
            year: 年份，默认当前年
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            月报内容字符串
        """
        print("🚀 开始生成月报...")
        
        try:
            # 使用工厂模式创建月报生成器
            generator = ReportGeneratorFactory.create_generator("monthly")
            
            # 生成月报
            report = generator.create_report(
                month=month,
                year=year,
                owner=owner,
                repo=repo
            )
            
            print("✅ 月报生成完成!")
            return report
            
        except Exception as e:
            print(f"❌ 月报生成失败: {str(e)}")
            return f"月报生成失败: {str(e)}"
    
    def generate_changelog(self, pr_num_list: list, owner: str = "alibaba", repo: str = "higress") -> str:
        """
        生成changelog
        
        Args:
            pr_num_list: PR编号列表
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            changelog内容字符串
        """
        print("🚀 开始生成changelog...")
        
        try:
            # 使用工厂模式创建changelog生成器
            generator = ReportGeneratorFactory.create_generator("changelog")
            
            # 生成changelog
            report = generator.create_report(
                pr_num_list=pr_num_list,
                owner=owner,
                repo=repo
            )
            
            print("✅ Changelog生成完成!")
            return report
            
        except Exception as e:
            print(f"❌ Changelog生成失败: {str(e)}")
            return f"Changelog生成失败: {str(e)}"
    
    def interactive_mode(self):
        """交互模式 - 让用户选择生成什么类型的报告"""
        print("🎉 欢迎使用Higress报告生成器!")
        print("支持的报告类型:")
        print("1. 月报 (monthly)")
        print("2. Changelog (changelog)")
        print("3. 退出 (exit)")
        
        while True:
            try:
                choice = input("\n请选择要生成的报告类型 (1/2/3): ").strip()
                
                if choice == "1":
                    # 生成月报
                    month_input = input("请输入月份 (回车使用当前月): ").strip()
                    year_input = input("请输入年份 (回车使用当前年): ").strip()
                    
                    month = int(month_input) if month_input else None
                    year = int(year_input) if year_input else None
                    
                    report = self.generate_monthly_report(month=month, year=year)
                    print("\n" + "="*50)
                    print("📋 月报内容:")
                    print("="*50)
                    print(report)
                    print("="*50)
                    
                elif choice == "2":
                    # 生成changelog
                    pr_nums_input = input("请输入PR编号列表 (用逗号分隔，如: 1234,1235,1236): ").strip()
                    
                    if not pr_nums_input:
                        print("❌ 请输入有效的PR编号列表")
                        continue
                    
                    try:
                        pr_num_list = [int(x.strip()) for x in pr_nums_input.split(",")]
                    except ValueError:
                        print("❌ PR编号格式不正确，请输入数字")
                        continue
                    
                    report = self.generate_changelog(pr_num_list=pr_num_list)
                    print("\n" + "="*50)
                    print("📋 Changelog内容:")
                    print("="*50)
                    print(report)
                    print("="*50)
                    
                elif choice == "3":
                    print("👋 感谢使用Higress报告生成器，再见!")
                    break
                    
                else:
                    print("❌ 无效选择，请输入 1、2 或 3")
                    
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 发生错误: {str(e)}")


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 创建报告代理
    agent = ReportAgent()
    
    # 启动交互模式
    agent.interactive_mode()


if __name__ == '__main__':
    main() 