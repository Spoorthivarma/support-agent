# ShopEasy Support Agent: your first AI agent (about 30 minutes)

This is a customer-support chatbot that can **take actions**. It looks up orders, checks store policy and creates support tickets. It's free to run: it uses Google's Gemini API on the free tier.

---

## Part 1: Set it up (about 15 minutes)

### Step 1: Install Python (skip this if you already have it)
- Download **Python 3.10 or newer** from https://www.python.org/downloads/
- **Windows:** on the first installer screen, tick **"Add Python to PATH"**.
- Check that it worked: open a terminal (Windows: *Command Prompt*, Mac: *Terminal*) and type:
  ```
  python --version
  ```
  (On Mac, use `python3` wherever this guide says `python`, and `pip3` wherever it says `pip`.)

### Step 2: Get a free Gemini API key
1. Go to **https://aistudio.google.com/app/apikey** and sign in with your Google account.
2. Click **Create API key** and copy it.
   *An API key works like a password that lets your code use the AI model. Never share it or upload it to GitHub.*

### Step 3: Put the project files in a folder
Put all the files (`agent.py`, `app.py`, `requirements.txt`, `.env.example`, `README.md`) in one folder, for example `support-agent` on your Desktop. Then open a terminal in that folder:
```
cd Desktop/support-agent
```

### Step 4: Install the libraries
```
pip install -r requirements.txt
```

### Step 5: Add your key
- Make a copy of `.env.example` and name the copy **`.env`** (just `.env`, with no other name before the dot).
- Open `.env` and paste in your key:
  ```
  GEMINI_API_KEY=AIza...your key...
  MODEL=gemini-flash-latest
  ```

### Step 6: Run it
**Option A: in the terminal**
```
python agent.py
```
**Option B: as a web chat page (better for demos)**
```
streamlit run app.py
```
A browser tab opens at http://localhost:8501.

### Step 7: Try these messages and watch the 🔧 tool lines
| You type | What the agent does |
|---|---|
| `Where is my order 1001?` | Calls `get_order_status` and answers from the result |
| `Can I cancel order 1003?` | Calls **two** tools (order status, then cancellation policy) and combines the results |
| `What's your refund policy?` | Calls `get_policy` |
| `I want to track my order` | Asks you for the order ID, because it knows the tool needs one |
| `My earbuds from 1001 arrived broken` | Checks the order, then creates a ticket for a human |
| `Hi, how are you?` | Calls no tool and just chats |

The agent **decides by itself** which tool to use, in what order, and when to stop. Nothing in the code says "if the message contains 'cancel', check the policy."

### Optional: put it online for free (about 10 minutes)
1. Upload the files to a GitHub repository. **Do not upload `.env`.**
2. Go to https://share.streamlit.io, sign in with GitHub, click **Create app**, pick your repo, and set the main file to `app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```
   GEMINI_API_KEY = "AIza...your key..."
   ```
   Then add these 2 lines to the top of `agent.py`, right after `load_dotenv()`, so the deployed app can read the secret:
   ```python
   try:
       import streamlit as st; os.environ.setdefault("GEMINI_API_KEY", st.secrets["GEMINI_API_KEY"])
   except Exception: pass
   ```
4. Click **Deploy**. You get a public link you can share or put on your resume.

### If something goes wrong
| Error | Fix |
|---|---|
| `python is not recognized` | Reinstall Python and tick "Add to PATH", or use `py` instead of `python` |
| `Missing GEMINI_API_KEY` | The file must be named exactly `.env`, sit in the same folder, and contain your key |
| `404 model not found` | Model names change over time. In `.env`, try `MODEL=gemini-2.5-flash` or pick another model from https://ai.google.dev/gemini-api/docs/models |
| `429` / quota error | You hit the free-tier limit. Wait a minute and try again |

---

## Part 2: Understand it (to explain it in an interview)

### Chatbot vs. agent, in one line
> A **chatbot** only *generates text*. An **agent** uses an LLM to *decide what actions to take*, takes them through tools, looks at the results, and repeats until the goal is done.

### The 4 building blocks (all in `agent.py`)
1. **LLM (the brain):** Gemini. It reasons and decides what to do next.
2. **Tools (the hands):** ordinary Python functions (`get_order_status`, `get_policy`, `create_support_ticket`). The LLM never sees the code. It only sees each tool's **name, description and parameter schema (JSON)**, and it picks a tool based on those descriptions.
3. **Memory:** the `messages` list. It holds the whole conversation, including tool calls and their results, and is sent to the LLM every turn. That's why the agent remembers that you said "order 1003" earlier.
4. **The agent loop (the key part):**
   ```
   while not done:
       send conversation + tool list to the LLM
       if the LLM asks for a tool  -> run it, add the result to memory, loop again
       else                        -> that's the final answer, stop
   ```
   This is called the **ReAct** pattern (Reason + Act): think → act → observe → repeat.

### What actually happens for "Can I cancel order 1003?"
1. The LLM reads the question and replies with *no text*, just a request: call `get_order_status(order_id="1003")`.
2. **Our code** (not the LLM) runs the function. Result: `status: Processing`.
3. We send the result back. The LLM now asks for `get_policy(topic="cancellation")`.
4. We run it. Result: "cancel only while Processing."
5. The LLM has enough information and answers: "Yes, order 1003 is still processing, so it can be cancelled."

**Important point for interviews:** the LLM never runs anything itself. It only *requests* a tool call as structured JSON. Your application runs the tool. That's what keeps agents controllable and safe.

### Questions you may be asked
- **"What is function calling / tool calling?"** You describe functions to the LLM as a JSON schema. The model returns a structured call (name + arguments) instead of text. Your code runs the call and returns the result.
- **"How do you stop an agent from looping forever?"** Set a step limit (`MAX_STEPS = 5` here), use timeouts, and fall back to a human.
- **"How do you make agents safe?"** Give them only the tools they need (least privilege), validate tool arguments, require human approval for risky actions (refunds, deletions), and log every tool call.
- **"How would this become production-ready?"** Swap the fake dictionaries for real database or API calls. Add **RAG** (retrieval-augmented generation, i.e. searching your FAQ and docs for the answer) for policy questions. Store memory in a database per user. Add monitoring, evaluation and guardrails.
- **"Have you used frameworks?"** "I built the loop from scratch to understand it. Frameworks like **LangChain/LangGraph, CrewAI, the OpenAI Agents SDK, Google ADK** and the **Claude Agent SDK** wrap this same loop and add memory, multi-agent setups and tracing."
- **"What is MCP?"** The **Model Context Protocol** is an open standard for connecting tools and data sources to AI apps. You write a tool once as an MCP server, and any MCP-compatible agent can use it.
- **"What's a multi-agent system?"** Several specialised agents, for example a "billing agent" and a "tech-support agent", plus a router or orchestrator that sends each request to the right one.

### How to describe this project in 30 seconds
> "I built a customer-support agent in Python on top of Gemini's tool-calling API. It has three tools: order lookup, policy lookup and ticket escalation. I wrote the agent loop myself: the model decides which tool to call, my code runs it and returns the result, and it repeats until the model can answer. Conversation memory carries context across turns, and a step limit prevents runaway loops. I added a Streamlit UI that shows each tool call, so you can watch the agent reason."

### Small changes to try (each one makes you more confident)
1. Add order `"1004"` to `ORDERS` and ask about it.
2. Add a new tool, `cancel_order(order_id)`, that changes the status to "Cancelled". You need 3 things: the function, an entry in `TOOL_FUNCTIONS`, and a description in `TOOLS`. Then ask the agent to cancel order 1003.
3. Change `SYSTEM_PROMPT` (for example, "always reply in Hindi") and see how the behaviour changes.
