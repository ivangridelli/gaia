from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from typing_extensions import TypedDict, Annotated
import operator
from langchain_openai import ChatOpenAI

# Import your tools
from tools.calculate import calculate
from tools.wikipedia import wikipedia
from tools.notes import add_note, get_notes
from tools.calendar import set_reminder
from tools.websearch import web_search

# LLM
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

# List of tools
tools = [calculate, wikipedia, add_note, get_notes, set_reminder, web_search]
tools_by_name = {tool.name: tool for tool in tools}

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Agent State
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# Nodes
def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: AgentState):
    results = []
    last_message = state["messages"][-1]
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool = tools_by_name[tool_name]
        result = tool.invoke(tool_args)
        results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    return {"messages": results}

# Conditional edge
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# Build the StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# Compile agent
agent = workflow.compile()
