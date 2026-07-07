from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import Env

API_KEY =  Env.API_KEY # 请替换为你的真实Key

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url="https://ws-38q8iso84wz2gvny.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",  # 这是阿里云的兼容接口
    model="qwen-plus",
    temperature=0.7
)


class ReviewResult(BaseModel):
    # Literal 限制大模型只能输出这两个词中的一个
    action: Literal["PASS", "REVISE"] = Field(description="如果文章合格输出 PASS，需要修改输出 REVISE")
    feedback: str = Field(description="如果是 REVISE，请给出详细的修改建议；如果是 PASS，输出'无'")


def reviewer_node(state: dict):
    print("--- 🧐 正在运行 Reviewer 节点 ---")

    topic = state.get("topic")
    draft = state.get("draft")

    # 系统提示词里必须带上 "JSON" 关键字
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个苛刻的文章主编。请审核提供的草稿是否满足以下标准：
        1. 是否准确回答了问题？
        2. 结尾是否包含来源链接？
        如果满足，action 输出 PASS。
        如果不满足，action 输出 REVISE，并在 feedback 中指出具体哪里需要修改。
        请务必以 JSON 格式输出。"""),
        ("user", "问题: {topic}\n\n草稿内容:\n{draft}")
    ])

    structured_llm = llm.with_structured_output(ReviewResult)
    chain = prompt | structured_llm

    result = chain.invoke({"topic": topic, "draft": draft})

    print(f"   质检结果: {result.action}")
    if result.action == "REVISE":
        print(f"   修改意见: {result.feedback}")

    return {
        "review_action": result.action,
        "review_feedback": result.feedback
    }


if __name__ == '__main__':
    test_state = {
        "topic": "2026年的固态电池发展的现状是什么",
        "revision_count": 0,
        "raw_data": [
            "【信息来源】: 无\n【正文内容】: 预计到2026年，固态电池将初步实现商业化，成本会有所下降。"
        ]
    }
