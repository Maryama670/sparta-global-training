"""
The tool use loop... nothing is here knows about FastAPI
"""

import knowledge_store as knowledge
from llm import MODEL, client


# Agent system prompt
AGENT_SYSTEM_PROMPT = (
    "You are a legal market analyst with access to tools to search tool over a firm."
    "Intelligence knowledge base. Use the tool whenever a question needs"
    "information you don't already have - do not guess. Cite document ids in"
    "your final answer. If the tool returns nothing relevant, say so honestly."
)

# Search tool
SEARCH_TOOL = {
    "name": "search_knowledge_base",
    "description": (
        "Search the firm intelligence knowledge base for documents relevant"
        "to a question about firms, jurisdictions, compliance, or market commentary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "the search query"},
        },
        "required": ["query"],
    },
}

MAX_ITERATIONS = 4


# the loop - one call, check, maybe repeat
def ask_with_tools(question: str) -> dict:
    """
    Run the tool-use loop intill the model answers, or the limit is hit
    """
    messages = [{"role": "user", "content": question}]
    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_made = 0

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=AGENT_SYSTEM_PROMPT,
            messages=messages,
            tools=[SEARCH_TOOL],
        )
        last_stop_reason = response.stop_reason
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # checking whether the model is done
        if response.stop_reason != "tool_use":
            final_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return {
                "answer": final_text,
                "complete": True,
                "tool_calls_made": tool_calls_made,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "stop_reason": response.stop_reason
            }
        # response  content  - when added a message with role assistant,
        # content is a list of blocks, each block has a type and text
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []

        for tool_block in tool_blocks:
            result_text, is_error = _execute_tool(tool_block.name, tool_block.input)
            if not is_error:
                tool_calls_made += 1
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_text,
                "is_error": is_error,
            })

        messages.append({ "role": "user", "content": tool_results })
    return {
          "answer": "Could not reach a final answer within the iteration limit.",
          "complete": False,
          "tool_calls_made": tool_calls_made,
          "input_tokens": total_input_tokens,
          "output_tokens": total_output_tokens,
          "stop_reason": last_stop_reason,
      }


def _execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """
    Run the requested tool, returns (result_text, is_error)
    """

    # Guard 1: we only have ine real tool, checking it is qual to  that
    if name != "search_knowledge_base":
        return f"Unknown tool: {name}", True

    # Guard 2: even the right tool is useless without its one argument
    if "query" not in tool_input:
        return 'Error: missing required field "query"', True

    try:
        results = knowledge.search(tool_input["query"], top_k=3)

    # same RuntimeError that knowledge.search has always raised
    # it gets cought here instead of letting it crash the whole agent loop
    except RuntimeError as e:
        return f"Error: {e}", True

    # A search that WORKED but found nothing .... the is_error is False here
    # this is an honest empty result.... nothing went wrong
    if not results:
        return "No relevant documents found", False

    # the real success path ... genuine results, formatted for the model to read
    formatted = "\n\n".join(
        f"[{r['id']}] {r['title']} (score {r['score']:.2f})\n{r['text']}"
        for r in results
    )
    return formatted, False