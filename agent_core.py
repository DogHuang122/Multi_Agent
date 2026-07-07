import operator
from typing import TypedDict, List, Annotated
# 导入 LangGraph 的核心组件
from langgraph.graph import StateGraph, START, END
from Summary import Summary_node
from Planner import planner_node
from Reviewer import reviewer_node
from Search import researcher_node
from test_writer_reviewer import writer_node


# 定义全局状态
class AgentState(TypedDict):
    topic: str  # 用户输入的原始问题
    research_plan: List[str]  # Planner 拆解出的搜索关键词列表
    raw_data: Annotated[List[str], operator.add]  # Researcher 搜集到的原始文本
    summary: str
    draft: str  # Writer 写出的初稿
    review_feedback: str  # Reviewer 给出的修改建议
    revision_count: int  # 修改次数

def route_after_review(state: dict):
    if state.get("revision_count", 0) >= 3:
        print("达到最大修改次数，强制结束。")
        return END
    if state.get("review_action") == "PASS":
        print("质检通过！")
        return END
    return "writer_node"


workflow = StateGraph(AgentState)
# 2. 注册节点 (给节点起个名字字符串，然后绑定对应的函数)
workflow.add_node("planner_node", planner_node)
workflow.add_node("researcher_node", researcher_node)
workflow.add_node("writer_node", writer_node)
workflow.add_node("reviewer_node", reviewer_node)
workflow.add_node("summary_node", Summary_node)

# 3. 添加普通边 (线性的流程)
workflow.add_edge(START, "planner_node")
workflow.add_edge("planner_node", "researcher_node")
workflow.add_edge("researcher_node", "summary_node")
workflow.add_edge("summary_node", "writer_node")

# 4. 添加条件边
workflow.add_conditional_edges(
    "reviewer_node",
    route_after_review,
    {
        "writer_node": "writer_node",
        END: END
    }
)

workflow.add_edge("writer_node", "reviewer_node")


app = workflow.compile()


if __name__ == '__main__':

    inputs = {
        "topic": "AiAgent的发展趋势，就业趋势",
        "revision_count": 0
    }

    print("\n================🚀 SYSTEM START 🚀================\n")


    final_draft = ""

    # 开始流式运行
    for output in app.stream(inputs):

        for node_name, node_update in output.items():
            print(f"\n▶️ [节点 {node_name}] 刚刚执行完毕！")

            # --- 1. 监控 Planner---
            if node_name == "planner_node":
                print("   🧠 AI 拆解的搜索策略：", node_update.get("research_plan"))

            # --- 2. 监控 Researcher---
            elif node_name == "researcher_node":
                data_count = len(node_update.get("raw_data", []))
                print(f"   🕵️‍♂️ AI 成功抓取了 {data_count} 个网页片段。")

            elif node_name == "summary_node":
                print(f"   🕵️‍♂️ AI总结的文本内容为:{node_update.get('summary')}")

            # --- 3. 监控 Writer---
            elif node_name == "writer_node":
                print("   ✍️ AI 刚刚写完了一版草稿。")
                final_draft = node_update.get("draft", "")

            # --- 4. 监控 Reviewer---
            elif node_name == "reviewer_node":
                action = node_update.get("review_action")
                if action == "REVISE":
                    print("   ❌ 质检 [未通过]！打回重写。")
                    print("   🤬 主编意见：", node_update.get("review_feedback"))
                else:
                    print("   🎉 质检 [通过]！")

    print("\n================✅ SYSTEM END ✅================\n")
    print("============= 🏆 最终研报结果 🏆 =============")
    print(final_draft)