from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from agent import AgentState
import Env
API_KEY = Env.API_KEY

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url="https://ws-38q8iso84wz2gvny.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",  # 这是阿里云的兼容接口
    model="qwen-plus",
    temperature=0.7
)

class Plan(BaseModel):
    queries: list[str] = Field(description="用于搜索引擎检索的 3 个核心关键词")

def print_prompt(prompt):
    print(prompt)
    return prompt


def planner_node(state: AgentState):
    print("--- 🧠 运行 Planner 节点 ---")
    topic = state["topic"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深的研究规划师。请将用户的宏大问题拆解为 3 个最有助于在搜索引擎上查询的关键词,请你务必以JSON格式输出。"),
        ("user", "问题: {topic}")
    ])

    # 强制 LLM 输出 JSON 数组结构
    structured_llm = llm.with_structured_output(Plan)
    chain = prompt | structured_llm
    result = chain.invoke({"topic": topic})
    # 返回字典，LangGraph 会自动更新到 State 中对应的字段
    return {"research_plan": result.queries}

if __name__ == '__main__':

    test_agent = {
        "topic": "2026年的固态电池发展的现状是什么",
    }
    result = planner_node(test_agent)