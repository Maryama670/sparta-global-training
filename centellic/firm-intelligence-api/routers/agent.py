"""The tool-use loop..nothing in here knows about the FASTAPI"""

import knowledge_store as knowledge  # Load the project's in-memory document search and embedding helpers.
# Import the model name and configured Anthropic client.
from llm import MODEL, client


# agent system prompt
AGENT_SYSTEM_PROMPT = (  # Store the system prompt used by the function below.
    "You are legal makrte analyst with access to tools to a search tool over a firm "
    "intelligence knowledge base. Use the tool whenevr a question needs "
    "information you don't already have - do not guess. Cite document ids in  "
    "your final answer. If the tool returns nothing relevant, say so honestly."
)


# search tool
SEARCH_TOOL = {  # Define the search tool advertised to the model.
    "name": "search_knowledge_base",  # Match this name to the name checked in _execute_tool.
    "description": (  # Help the model decide when to request a search.
        "Search the firm intelligence knowledge base for documents relevant "
        "to a question about firms, jurisdictions, compliance, or market commentary."
    ),
    "input_schema": {  # Describe the expected tool arguments using JSON Schema.
        "type": "object",  # Arguments are named fields in an object.
        "properties": {
            "query": {"type": "string", "description": "The search query"},  # Supply the text to search for.
        },
        "required": ["query"],  # A search request must contain a query.
    }
}


# the loop - one call, check, maybe repeat
MAX_ITERATIONS = 4  # Allow at most four model requests per question.


def ask_with_tools(question: str) -> dict:
    """Run the tool-use loop until the model answers, orrrr the limit is hit"""
    messages = [{"role": "user", "content": question}]  # Start the conversation with the user's question.
    total_input_tokens = 0  # Accumulate input token usage across model requests.
    total_output_tokens = 0  # Accumulate generated token usage across model requests.
    total_calls_made = 0  # Count successful tool calls.

    # the loop
    for _ in range(MAX_ITERATIONS):  # Repeat until an answer is returned or the request limit is reached.
        response = client.messages.create(  # Ask the model to answer or request the advertised tool.
            model=MODEL,  # Use the model configured in llm.py.
            max_tokens=600,  # Limit the output tokens for this individual request.
            system=AGENT_SYSTEM_PROMPT,  # Supply the agent's instructions.
            tools=[SEARCH_TOOL],  # Advertise the search tool; this does not execute the search.
            messages=messages,  # Send the conversation accumulated so far.
        )

        total_input_tokens += response.usage.input_tokens  # Add this request's input usage.
        total_output_tokens += response.usage.output_tokens  # Add this request's output usage.

        # Check whether the model actually requested any tools.
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_blocks:
            final_text = next(  # Take only the first text block, with an empty-string fallback.
                (b.text for b in response.content if b.type == "text"), ""
            )

            return {
                "answer": final_text,  # Return the extracted model text.
                "completed": True,  # This flag does not currently distinguish a truncated answer.
                "tool_calls_made": total_calls_made,  # Report the number of successful tool calls.
                "input_tokens": total_input_tokens,  # Report accumulated model input usage.
                "output_tokens": total_output_tokens,  # Report accumulated model output usage.
                "stop_reason": response.stop_reason,  # Preserve the provider's reason for stopping.
            }


        
        # Keep the assistant's tool request in the conversation before adding a tool result.
#A tool block is the model’s structured instruction saying: “Use this tool, with these arguments.”Example:search_knowledge_base(query="How is PEP calculated?")
#So it contains the tool name + inputs the tool needs.
        messages.append({"role": "assistant", "content": response.content})  # Preserve all response blocks.#

        tool_results = []
        for tool_block in tool_blocks:
            result_text, is_error = _execute_tool(tool_block.name, tool_block.input)
            if not is_error:
                total_calls_made += 1

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_text,
                "is_error": is_error,
            })
        messages.append({
            "role": "user",
            "content": tool_results,
        })
        # If the model requests several tools, each request needs its own result.
    # Unfinished: exhausting the loop currently returns None, despite the declared dict return type.


#guard 1 - we only have one real tool checking its equal to that - sam
def _execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run the requested tool. Returns (result_text, is_error)"""
    if name != "search_knowledge_base":  # Reject tool names this helper does not implement.
        return f"Unknown tool: {name}", True  # Mark the result as an error for the model.
#Guard 2 even the right tool is useless without its one arguemnt - sam
    if "query" not in tool_input:  # Check that the required field is present; its type is not checked here.
        return 'Error: missing required field "query"', True

    try:
        results = knowledge.search(tool_input["query"], top_k=3)  # Retrieve up to three highest-scoring documents.
    except RuntimeError as e:  # Handle errors such as an index that has not been built.
        return f"Error: {e}", True  # Return the error as text; other exception types still propagate.
# same Runtimeerro that knowledge.search has always raised 
#it gets caught here instead of letting it crash the whole agent loop - sam
    if not results:  # Check for an empty result list; no similarity threshold is applied here.
        return "No relevant documents found", False  # An empty search is a valid result, not a tool error.
    #a search that worked but found nothing is_error is false here - sam

    formatted = "\n\n".join(  # Separate the retrieved documents with blank lines.
        f"[{r['id']}] {r['title']} (score {r['score']:.2f})\n{r['text']}"  # Include citation ID, title, score and text.
        for r in results  # Format each search hit; .2f displays the score to two decimal places.
    )
    return formatted, False  # Return the document text and a flag indicating success.
# the real success path - genuinve results, formatted for the model to read ...
