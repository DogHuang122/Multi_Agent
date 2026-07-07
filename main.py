import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from agent_core import app as agent_app

app = FastAPI(title="Agent 写作 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    topic: str


async def run_langgraph_agent(topic: str):

    inputs = {
        "topic": topic,
        "revision_count": 0
    }

    final_draft = ""

    # 通知前端：系统启动
    yield f"data: {json.dumps({'type': 'log', 'msg': '🚀 收到需求，Agent 系统启动！'})}\n\n"

    try:
        # ⚠️ 使用 astream() 进行异步流式输出，防止阻塞 FastAPI
        async for output in agent_app.astream(inputs):
            for node_name, node_update in output.items():

                # --- 1. 监控 Planner ---
                if node_name == "planner_node":
                    plan = node_update.get("research_plan", [])
                    msg = f"🧠 Planner 拆解了 {len(plan)} 个搜索策略：{', '.join(plan)}"
                    yield f"data: {json.dumps({'type': 'log', 'msg': msg})}\n\n"

                # --- 2. 监控 Researcher ---
                elif node_name == "researcher_node":
                    data_count = len(node_update.get("raw_data", []))
                    msg = f"🕵️‍♂️ Researcher 成功抓取了 {data_count} 条相关资料。"
                    yield f"data: {json.dumps({'type': 'log', 'msg': msg})}\n\n"

                # --- 3. 监控 Summary ---
                elif node_name == "summary_node":
                    msg = f"📝 AI 已经完成资料的阅读和总结归纳。"
                    yield f"data: {json.dumps({'type': 'log', 'msg': msg})}\n\n"

                # --- 4. 监控 Writer ---
                elif node_name == "writer_node":
                    msg = f"✍️ Writer 刚刚完成了一版草稿，已提交给主编审核..."
                    final_draft = node_update.get("draft", "")
                    yield f"data: {json.dumps({'type': 'log', 'msg': msg})}\n\n"

                # --- 5. 监控 Reviewer ---
                elif node_name == "reviewer_node":
                    action = str(node_update.get("review_action", "")).strip().upper()
                    if action == "PASS":
                        msg = f"🎉 主编质检【通过】！文章即将生成。"
                        yield f"data: {json.dumps({'type': 'log', 'msg': msg})}\n\n"
                    else:
                        # 其他情况全部视为未通过
                        feedback = node_update.get("review_feedback", "未提供具体意见")
                        msg = f"❌ 主编质检【未通过】，打回重写。意见：{feedback}"
                        yield f"data: {json.dumps({'type': 'log', 'msg': msg, 'is_error': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'log', 'msg': f'⚠️ 运行出错: {str(e)}', 'is_error': True})}\n\n"

    # 执行完毕，将最终的草稿发送给前端进行 Markdown 渲染
    if final_draft:
        yield f"data: {json.dumps({'type': 'final', 'content': final_draft})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'log', 'msg': '⚠️ 未能生成有效文章。', 'is_error': True})}\n\n"


@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/generate")
async def generate_article(req: AgentRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="主题不能为空")

    return StreamingResponse(
        run_langgraph_agent(req.topic),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)