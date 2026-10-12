# get_api(1차 분류) 이후 서브그래프: 2차 분류(QUERY/ACTION/GENERAL)와 그 라우팅

from langgraph.graph import END, StateGraph, START

from app.ai.langgraph.state import ChatGraphState
from app.ai.langgraph.sql_graph import sql_graph

from app.ai.langgraph.action_graph import action_graph
from app.ai.api_use.chat_classify import classify_intent
from app.ai.llm_use.llm_calling_langchain import generate_general_response


# 2차분류 : QUERY, ACTION, GENERAL
def classify_intent_node(state: ChatGraphState) -> dict:
    print("[LangGraph][GetApi] ===== get_api_graph 시작 =====")
    intent = classify_intent(state["message"])
    print(f"[LangGraph][GetApi] 2차 분류 결과: {intent}")
    return {"intent": intent}


def run_action_node_hitl(state: ChatGraphState) -> dict:
    # HITL 순서0. action_graph 최초실행
    # action_graph는 회원별로 확인 대기(interrupt) 상태를 이어갈 수 있어야 하므로
    # member_id 기반 thread_id로 확인. db는 checkpoint에 저장되면 안 되므로 config로 전달.
    thread_id = f"member-{state['member_id']}"
    result = action_graph.invoke(
        {
            "message": state["message"],
            "member_id": state["member_id"],
        },
        # RunnableConfig객체를 주입
        config={"configurable": {"thread_id": thread_id, "db": state["db"]}},
    )

    # HITL 순서1 interrupt 감지, 상위 그래프에 pending_confirm 전달
    # execute_action 진입 전 interrupt()가 걸려 result에 __interrupt__가 담겨 돌아올땐 main_graph까지 "확인 대기" 상태를 그대로 전달
    if result.get("__interrupt__"):
        confirm_payload = result["__interrupt__"][0].value
        print(f"[LangGraph][GetApi] action 실행 확인 대기 | {confirm_payload}")
        return {"pending_confirm": confirm_payload}

    # escalate 플래그도 함께 전달 (main_graph가 재시도까지 소진한 실패를 감지할 수 있도록).
    return {"response": result["response"], "escalate": result.get("escalate", False)}


def run_general_node(state: ChatGraphState) -> dict:
    print("[LangGraph][GetApi] run_general 진입")
    response = generate_general_response(state["message"])
    return {"response": response}


def route_after_intent(state: ChatGraphState) -> str:
    intent = state.get("intent")
    if intent == "QUERY":
        decision = "query"
    elif intent == "ACTION":
        decision = "action"
    else:
        decision = "general"
    print(f"[LangGraph][GetApi] route_after_intent -> {decision}")
    return decision


def build_get_api_graph():
    graph = StateGraph(ChatGraphState)

    graph.add_node("classify_intent", classify_intent_node)
    # 컴파일된 서브그래프를 노드로 직접 추가
    graph.add_node("sql_graph", sql_graph)
    # graph.add_node("action_graph", action_graph)
    # HITL인 경우
    graph.add_node("action_graph", run_action_node_hitl)
    graph.add_node("run_general", run_general_node)

    # START : 그래프를 실행할 때의 진입점
#   classify_intent ──(QUERY)───▶ sql_graph ────┐
#         │──────────(ACTION)───▶ action_graph ─┤
#         └──────────(GENERAL)──▶ run_general ──┤
#                                               ▼
#                                              END

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {"query": "sql_graph", "action": "action_graph", "general": "run_general"},
    )
    graph.add_edge("sql_graph", END)
    graph.add_edge("action_graph", END)
    graph.add_edge("run_general", END)
    return graph.compile()


get_api_graph = build_get_api_graph()
