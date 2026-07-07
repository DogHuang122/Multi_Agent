import hashlib
import os
from langchain_tavily import TavilyResearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
import Env
from pymilvus import MilvusClient
from langchain_huggingface import HuggingFaceEmbeddings

Tvly_API_KEY = Env.Tvly_API_KEY
VECTOR_DIMENSION = Env.VECTOR_DIMENSION
embedding_model = HuggingFaceEmbeddings(model_name = "BAAI/bge-small-zh-v1.5")

milvus_client = MilvusClient("http://localhost:19530")
Collection_name = Env.COLLECTION_NAME

if not milvus_client.has_collection(Collection_name):
    milvus_client.create_collection(
        collection_name=Collection_name,
        dimension=512,
        id_type="string",
        max_length = 64
    )

def generate_md5_id(text:str)->str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def researcher_node(state: dict):
    print("--- 🕵️‍♂️ 正在运行 Researcher 节点 (爬取 -> 去重 -> 长期存储) ---")
    queries = state.get("research_plan", [])
    if not queries:
        return {"raw_data": []}

    search_tool = TavilyResearch(max_results=2, tavily_api_key=Tvly_API_KEY)

    raw_documents = []
    for q in queries:
        try:
            results = search_tool.invoke({"query": q})
            for r in results:
                raw_documents.append({"url": r.get("url", ""), "content": r.get("content", "")})
        except Exception as e:
            print(f"   ❌ 搜索出错: {e}")

    if not raw_documents:
        return {"raw_data": []}

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    chunks = []
    for doc in raw_documents:
        split_texts = text_splitter.split_text(doc["content"])
        for text in split_texts:
            chunks.append({"text": text, "url": doc["url"]})

    chunk_texts = [c["text"] for c in chunks]
    vectors = embedding_model.embed_documents(chunk_texts)

    milvus_data = []
    seen_ids_in_batch = set()
    for chunk, vector in zip(chunks, vectors):
        unique_id = generate_md5_id(chunk["text"])
        if unique_id not in seen_ids_in_batch:
            seen_ids_in_batch.add(unique_id)
            milvus_data.append({
                "id": unique_id,
                "vector": vector,
                "text": chunk["text"],
                "url": chunk["url"]
            })

    # upsert 机制：如果库里已经有这个 ID，就更新(相当于忽略重复)；如果没有，就插入新数据。
    milvus_client.upsert(collection_name=Collection_name, data=milvus_data)

    print(f"   ✅ 成功向长期知识库 upsert 了 {len(milvus_data)} 条数据（已自动根据文本去重）。")
    print("--- 🕵️‍♂️ Researcher 节点执行完毕 ---")

    # 由于检索放到下一步了，这里我们不需要传递抓取的内容，可以直接传递状态信息
    return {"raw_data": ["数据已成功入库。等待 Summary 节点检索。"]}

# ==========================================
# 2. 你的本地测试入口
# ==========================================
if __name__ == '__main__':
    test_state = {
        "topic": "2026年的固态电池发展的现状是什么",
        "research_plan": [
            "2026年 固态电池 发展现状",
            "固态电池 技术突破 2026",
            "固态电池 商业化 现状"
        ]
    }

    # 2. 调用函数
    final_update = researcher_node(test_state)

