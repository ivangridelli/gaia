from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from typing_extensions import TypedDict, Annotated
import operator
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import logging

# Import your tools
from tools.calculate import calculate
from tools.wikipedia import wikipedia
from tools.notes import add_note, get_notes
from tools.calendar import set_reminder
from tools.websearch import web_search

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM with better configuration
llm = ChatOpenAI(
    model="gpt-4o-mini",  # Updated model name
    temperature=0,
    max_retries=2,
    request_timeout=30
)

# List of tools
tools = [calculate, wikipedia, add_note, get_notes, set_reminder, web_search]
tools_by_name = {tool.name: tool for tool in tools}

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)


# Enhanced Agent State with conversation history limit
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


# System prompt for better agent behavior
SYSTEM_PROMPT = """You are Gaia, a helpful AI assistant with access to various tools.

When using tools:
- Use calculate for math operations
- Use wikipedia for factual information
- Use add_note to save information and get_notes to retrieve saved information
- Use set_reminder to schedule future reminders (accepts: '30s', '5m', '2h', 'tomorrow at 3pm')
- Use web_search for current information or when wikipedia doesn't have what you need

IMPORTANT: When setting reminders, if the tool returns an error about time being in the past, 
check the current time first with get_current_time, then calculate the correct future time.

Be concise but helpful. If a tool fails after 2-3 attempts, explain the issue to the user rather than retrying endlessly."""


def agent_node(state: AgentState):
    """Agent decision node with error handling and system prompt injection"""
    try:
        messages = state["messages"]

        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        # Limit conversation history to last 20 messages to avoid token limits
        if len(messages) > 20:
            system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
            recent_msgs = messages[-19:]  # Keep last 19 + system message = 20
            messages = system_msgs + recent_msgs

        logger.info(f"Agent processing {len(messages)} messages")
        response = llm_with_tools.invoke(messages)

        # Log tool calls for debugging
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Agent requesting tools: {[tc['name'] for tc in response.tool_calls]}")

        return {"messages": [response]}

    except Exception as e:
        logger.error(f"Error in agent_node: {e}")
        # Return error message to user
        error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Let me try to help you another way.")
        return {"messages": [error_msg]}


def tool_node(state: AgentState):
    """Tool execution node with error handling"""
    results = []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        try:
            tool = tools_by_name.get(tool_name)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' not found")

            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            result = tool.invoke(tool_args)
            logger.info(f"Tool {tool_name} result: {str(result)[:100]}...")

            results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            results.append(
                ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
            )

    return {"messages": results}


def should_continue(state: AgentState):
    """Conditional edge with max iteration check"""
    last_message = state["messages"][-1]

    # Safety check: prevent infinite loops (max 5 tool iterations)
    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    if len(tool_messages) >= 5:
        logger.warning(f"Max tool iterations reached ({len(tool_messages)} tool calls)")
        return END

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    return END


# Build the StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
workflow.add_edge("tools", "agent")

# Compile agent WITHOUT checkpointer for simplicity
# (Remove memory if you don't need conversation history across sessions)
agent = workflow.compile()