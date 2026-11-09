"""
ShopEasy Support Agent - a tiny agentic chatbot, written from scratch.

The whole idea of an "agent" fits in this file:

    1. The LLM (the "brain") reads the conversation.
    2. It can decide to CALL A TOOL (a normal Python function) instead of answering.
    3. We run that tool, give the result back to the LLM, and loop.
    4. When the LLM has enough information, it replies to the user.

That loop -> think -> act (tool) -> observe (result) -> repeat <- is what makes it
an agent rather than a plain chatbot. A plain chatbot can only talk; an agent can
DO things (look up data, create tickets, call APIs).

Run it:  python agent.py
"""

import json
import os
import random

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads GEMINI_API_KEY from the .env file

# ---------------------------------------------------------------------------
# 1. THE BRAIN: an LLM client
# ---------------------------------------------------------------------------
# We use Google's free Gemini API through the OpenAI-compatible endpoint, so this
# exact code also works with OpenAI, Groq, etc. by changing only these 3 values.
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL = os.getenv("MODEL", "gemini-flash-latest")

SYSTEM_PROMPT = """You are a friendly customer-support agent for ShopEasy, an online store.
- Use your tools to look up real order data. Never guess an order's status.
- If you need an order ID and the customer hasn't given one, ask for it.
- If you can't solve the problem, create a support ticket for a human.
- Keep replies short and polite."""

# ---------------------------------------------------------------------------
# 2. THE HANDS: tools the agent can use
# ---------------------------------------------------------------------------
# In a real company these would call databases or internal APIs.
# Here we use a fake in-memory "database" so you need nothing else installed.
ORDERS = {
    "1001": {"item": "Wireless Earbuds", "status": "Shipped", "eta": "Nov 12", "price": 2499},
    "1002": {"item": "Yoga Mat", "status": "Delivered", "eta": "Delivered Nov 5", "price": 899},
    "1003": {"item": "Smart Watch", "status": "Processing", "eta": "Nov 15", "price": 5999},
}

POLICIES = {
    "refund": "Refunds are allowed within 7 days of delivery. Money returns to the original payment method in 5-7 business days.",
    "shipping": "Standard shipping is free above Rs 499 and takes 3-5 business days.",
    "cancellation": "Orders can be cancelled only while they are still 'Processing'.",
}


def get_order_status(order_id: str) -> dict:
    """Look up an order in the database."""
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"No order found with ID {order_id}"}
    return {"order_id": order_id, **order}


def get_policy(topic: str) -> dict:
    """Return the store policy for a topic."""
    return {"topic": topic, "policy": POLICIES.get(topic, "No policy found for that topic.")}


def create_support_ticket(issue: str, order_id: str = "") -> dict:
    """Escalate to a human by creating a ticket."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    return {"ticket_id": ticket_id, "issue": issue, "order_id": order_id,
            "message": "A human agent will contact the customer within 24 hours."}


# Map tool names (what the LLM says) -> actual Python functions (what we run)
TOOL_FUNCTIONS = {
    "get_order_status": get_order_status,
    "get_policy": get_policy,
    "create_support_ticket": create_support_ticket,
}

# Tool DESCRIPTIONS sent to the LLM. The LLM never sees the Python code above,
# only these names, descriptions and parameter schemas. Good descriptions =
# the LLM picks the right tool.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the status, item, price and delivery date of a customer's order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "The order ID, e.g. 1001"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_policy",
            "description": "Get ShopEasy's official policy on refunds, shipping or cancellation.",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string", "enum": ["refund", "shipping", "cancellation"]}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Escalate to a human agent when you cannot solve the customer's problem yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string", "description": "Short summary of the problem"},
                    "order_id": {"type": "string", "description": "Related order ID, if any"},
                },
                "required": ["issue"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 3. THE LOOP: this is the "agentic" part
# ---------------------------------------------------------------------------
MAX_STEPS = 5  # safety limit so the agent can never loop forever


def run_agent(messages: list, on_step=print) -> str:
    """
    Run the agent until it produces a final answer.
    `messages` is the conversation MEMORY - it is updated in place.
    `on_step` is called with a description of every tool call (for display).
    """
    for _ in range(MAX_STEPS):
        # THINK: send the whole conversation + the list of tools to the LLM
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        reply = response.choices[0].message

        # Save the LLM's turn in memory (keeps any hidden fields Gemini needs)
        messages.append(reply.model_dump(exclude_none=True))

        # No tool requested -> the LLM is answering the user. We're done.
        if not reply.tool_calls:
            return reply.content

        # ACT: the LLM asked for one or more tools - run each one
        for call in reply.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            result = TOOL_FUNCTIONS[name](**args)
            on_step(f"🔧 Tool used: {name}({args}) -> {result}")

            # OBSERVE: give the tool's result back to the LLM
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })
        # ...and loop again so the LLM can read the results and decide what next

    return "Sorry, I couldn't finish that. Let me connect you to a human agent."


# ---------------------------------------------------------------------------
# 4. A simple chat in the terminal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Missing GEMINI_API_KEY. Put it in a .env file (see README).")

    print("ShopEasy Support Agent (type 'quit' to exit)")
    print("Try: 'Where is my order 1002?'  or  'Can I cancel order 1003?'\n")
    memory = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        if not user_input:
            continue
        memory.append({"role": "user", "content": user_input})
        answer = run_agent(memory, on_step=lambda s: print(f"   {s}"))
        print(f"Agent: {answer}\n")
