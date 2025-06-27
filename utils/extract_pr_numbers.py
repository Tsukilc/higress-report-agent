import re

def extract_pr_numbers(text):
    pr_nums = set()
    pr_nums.update(re.findall(r'#(\d+)', text))
    pr_nums.update(re.findall(r'pull/(\d+)', text))
    pr_nums = sorted(int(n) for n in pr_nums)
    return pr_nums

if __name__ == "__main__":
    # 把pr_link的文本放在pr_text变量中
    pr_text = """
pref: Optimize the memory paging tool (#498) by @Thomas-Eliot in #499
fix: Fix an incorrect text by @CH3CHO in #503
fix: Fix the bug of unable to enable ignore path case matching for AI routes by @CH3CHO in #508
fix: Fix some bugs in higress-config updating function by @CH3CHO in #509
fix: Update display name of OpenAI provider type by @CH3CHO in #510
Feature/issue 501 by @Thomas-Eliot in #504
fix: support jdk 8 by @Thomas-Eliot in #497
If service discovery from the registry is not used, the architecture allows decoupling from the Higress Controller. by @Thomas-Eliot in #506
feat: Add a simple note to the certificate edit form by @CH3CHO in #512
feat: Improve the K8s capabilities init logic by @CH3CHO in #513
feat: Support configuring multiple endpoints for custom OpenAI LLM providers by @CH3CHO in #517
feat: Update nacos3 service source form for nacos 3.0.1+ by @CH3CHO in #521
feat: Plugin server supports k8s deployment and configures the default download URL of the plugin by @NorthernBob in #520
feat: Update McpBridge according to the new CRD in Higress 2.1.4 by @CH3CHO in #522
fix: Add a missing annotation by @CH3CHO in #524
    """
    pr_num_list = extract_pr_numbers(pr_text)
    print(','.join(str(n) for n in pr_num_list))