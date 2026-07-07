import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import Env

API_KEY = Env.API_KEY  # 请替换为你的真实Key

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url="https://ws-38q8iso84wz2gvny.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",  # 这是阿里云的兼容接口
    model="qwen-plus",  # 或者用 qwen-turbo
    temperature=0.7
)

def writer_node(state: dict):
    print("--- ✍️ 正在运行 Writer 节点 ---")


    topic = state.get("topic")
    context = state.get("summary", "无参考资料")

    feedback = state.get("review_feedback", "")

    system_prompt = """你是一个严谨的行业分析师。请根据用户提供的问题和【背景信息】撰写一份专业报告。
    要求：
    1. 只能使用【背景信息】中的数据，绝不能捏造（无幻觉）。
    2. 在文章的末尾，必须列出你参考的【信息来源】链接。
    3. 输出格式为 Markdown。
    """

    if feedback:
        system_prompt += f"\n\n注意！这是上一次审核被拒的原因，请务必针对性修改：{feedback}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "问题: {topic}\n\n【背景信息】:\n{context}")
    ])

    chain = prompt | llm
    result = chain.invoke({"topic": topic, "context": context})

    print("   ✅ 初稿撰写完成！")
    return {
        "draft": result.content,
        "revision_count": state.get("revision_count", 0) + 1
    }