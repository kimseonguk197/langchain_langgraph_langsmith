import os
from openai import OpenAI
from .classification_list import TOOLS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_response(user_message: str, data: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"사용자의 질문에 대해 아래 참고 데이터를 바탕으로 사용자의 질문에 답변해. "
                           f"만약 참고데이터에 적절한 내용이 없으면 응답불가합니다 라고 답변해. \n\n[참고 데이터]\n{data}",
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        temperature=0.3,
        # max_completion_tokens=100
    )
    return response.choices[0].message.content.strip()



# def classify_message(message: str) -> str:
#     response = client.chat.completions.create(
#         model="gpt-4.1-mini",
#         messages=[
#             {
#                 "role": "system",
#                 "content": """
#                     사용자의 질문을 아래 3가지 중 하나로 분류하세요.
#                     get_my_orders:
#                     로그인한 사용자 본인의 주문 내역을 조회하는 질문
#                     get_my_profile:
#                     사용자 본인의 회원정보를 조회하는 질문
#                     get_policy:
#                     환불, 교환, 배송 등 사내정책에 대한 질문

#                     질문이 위 3가지 중 하나에 해당하면 해당 카테고리의 이름만 출력하세요.
#                     해당하지 않으면 "답변이 어려운 질문입니다."라고 출력하세요.

#                     반드시 분류 결과만 출력하고, 설명이나 다른 문장은 출력하지 마세요.
#                     """,
#             },
#             {
#                 "role": "user",
#                 "content": message,
#             },
#         ],
#         temperature=0,
#     )

#     return response.choices[0].message.content.strip()

def classify_message(message: str) -> str:
    response = client.chat.completions.create(
        # temperature는 분류 작업에 맞는 낮은 값으로 설정. 기본값은 1
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": message}],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0
        )
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        return "답변이 어려운 질문입니다."
    return tool_calls[0].function.name

