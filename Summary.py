from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from agent import AgentState
from langchain_huggingface import HuggingFaceEmbeddings
from pymilvus import MilvusClient
import Env

API_KEY = Env.API_KEY

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url="https://ws-38q8iso84wz2gvny.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    model="qwen-plus",
    temperature=0.7
)

# 2. 向量模型 (负责把问题转成向量去查库，必须跟 Researcher 节点用同一个！)
print("⏳ 正在加载本地 Embedding 模型...")
embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

# 3. 连接 Milvus 向量库
milvus_client = MilvusClient("http://localhost:19530")
COLLECTION_NAME = "global_knowledge_base"


# ==========================================
# 1. Summary 核心业务逻辑
# ==========================================
def Summary(State: dict):
    print("--- 📝 正在运行 Summary 节点 (Milvus 检索 + 大模型总结) ---")

    topic = State.get("topic", "未知问题")

    # ---------------- 阶段 1：向量检索 (RAG 的核心) ----------------
    print(f"🔍 正在从知识库中检索关于: [{topic}] 的相关资料...")

    # 1. 将用户问题转换为查询向量
    query_vector = embedding_model.embed_query(topic)

    # 2. 去 Milvus 里搜索最相关的 5 个文本块 (Top-K = 5)
    # 前提是确保库已经建好并有数据
    if milvus_client.has_collection(COLLECTION_NAME):
        # 必须先 load 进内存才能搜索
        milvus_client.load_collection(COLLECTION_NAME)
        search_results = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=[query_vector],
            limit=5,
            output_fields=["text", "url"]
        )
    else:
        search_results = [[]]

    # 3. 整理检索出来的资料
    retrieved_docs = []
    for hit in search_results[0]:
        text = hit["entity"]["text"]
        url = hit["entity"]["url"]
        retrieved_docs.append(f"【信息来源】: {url}\n【正文内容】: {text}")

    # 如果库里什么都没查到
    if not retrieved_docs:
        print("⚠️ 知识库中未检索到相关资料。")
        return {"summary": "抱歉，知识库中未检索到相关资料，无法生成客观的总结。"}

    raw_data_str = "\n\n".join(retrieved_docs)
    print(f"✅ 成功检索到 {len(search_results[0])} 条相关知识片段，已提交给大模型分析。")

    # ---------------- 阶段 2：大模型生成总结 ----------------
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """你是一个资深的行业分析师和总结员。
            请根据提供的【检索到的文章】，提炼出最核心的信息，以回答用户的【原始问题】。

            要求：
            1. 结论必须客观严谨，不能凭空捏造。
            2. 请使用 Markdown 格式输出。
            3. 🌟 关键要求：在总结的过程中，遇到引用的数据或观点，请在句末标注来源序号（如 [1]）。
            4. 🌟 关键要求：生成内容在保证质量的前提下尽量减小篇幅。
            5. 🌟 关键要求：必须在整篇总结的最末尾，单开一个【参考链接】模块，将你用到的【信息来源】URL 原样附上！绝对不能遗漏链接。"""),

            ("user", "【原始问题】: {topic}\n\n【检索到的文章】:\n{raw_data}")
        ]
    )

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"topic": topic, "raw_data": raw_data_str})

    return {
        "summary": result
    }

if __name__ == '__main__':
    test_state = {
        "topic": "AI Agent 相关岗位需求及薪资现状是什么？",
        "raw_data": [
            "AI Agent专家/架构师月薪：50-80K·18薪。职位描述：负责设计、开发和优化基于大模型的智能体解决方案...至少5年在AI领域的工作经验..."]
    }

    print("\n========== 开始测试 Summary 节点 ==========")
    final_update = Summary(test_state)

    print(final_update["summary"])