# Model calls are handled here, independently of FastAPI.

import os  # Load operating-system helpers so API keys can be read from environment variables.
import logging  # Load Python logging tools for reporting request costs and retry warnings.
import time  # Load time utilities so retries can pause before the next attempt.
import anthropic  # Load the Anthropic SDK, including its model client and exception classes.
from anthropic import APIStatusError, APITimeoutError, RateLimitError  # Import exceptions for provider HTTP errors, request timeouts and rate limits.
from pydantic import BaseModel, Field  # Import BaseModel for validated data schemas and Field for field constraints and descriptions.
MODEL = "claude-haiku-4-5-20251001"  # Select the Anthropic model used for generation.


# The SDK defaults are max_retries=2 and a 600-second read timeout.
# Both are deliberately overridden here.
client = anthropic.Anthropic(  # Create the Anthropic client with the settings below.
    api_key=os.environ["ANTHROPIC_API_KEY"],  # Read the provider API key from the environment.
    timeout=30.0,  # Set the provider request timeout in seconds.
    max_retries=3,  # Set how many times the SDK may retry a failed request.
)  # Close the preceding expression or collection.

#
# RULES GO IN SYSTEM
# DATA GOES IN USER

SYSTEM_PROMPT = (  # Assemble the instructions used for firm summaries and analyses.
    "You are a legal market analyst writing for an institutional audience. "  # Add this instruction to the prompt; adjacent strings form one text value.
    "Use British English. Use only the figures given to you. "  # Add this instruction to the prompt; adjacent strings form one text value.
    "Never invent numbers, rankings or facts that are not in the data provided."  # Add this instruction to the prompt; adjacent strings form one text value.
)  # Close the preceding expression or collection.


def build_prompt(firm: dict) -> str:  # Build the text prompt from a firm record.
    return (  # Build and return the text assembled below.
        "Summarise this law firm in two short paragraphs.\n\n"  # Add this instruction to the prompt; adjacent strings form one text value.
        f"Name: {firm['name']}\n"  # Insert this field value into the prompt text.
        f"Jurisdiction: {firm['jurisdiction']}\n"  # Insert this field value into the prompt text.
        f"Revenue: {firm['revenue_usd_m']}\n"  # Insert this field value into the prompt text.
        f"Lawyers: {firm['lawyers']}\n"  # Insert this field value into the prompt text.
        f"Equity Partners: {firm['equity_partners']}"  # Insert this field value into the prompt text.
    )  # Close the preceding expression or collection.


def summarise_firm(firm: dict) -> dict:  # Generate a firm summary and return its token usage.
    # Call the model and return the summary, token usage and stop reason.
    response = client.messages.create(  # Send the model request and retain the provider response.
        model=MODEL,  # Choose the model used for this request.
        max_tokens=400,  # Set the maximum number of output tokens for this request.
        system=SYSTEM_PROMPT,  # Supply the instructions that guide the model response.
        messages=[{"role": "user", "content": build_prompt(firm)}],  # Supply the user messages sent to the model.
    )  # Close the preceding expression or collection.
    return {  # Build and return a dictionary containing the following fields.
        "id": firm["id"],  # Include the record identifier in this record.
        "name": firm["name"],  # Include the name in this record.
        "summary": "\n".join(block.text for block in response.content if block.type == "text"),  # Include the generated summary in this record.
        "input_tokens": response.usage.input_tokens,  # Include the input token count in this record.
        "output_tokens": response.usage.output_tokens,  # Include the output token count in this record.
        "stop_reason": response.stop_reason,  # Include the reason generation stopped in this record.
    }  # Close the preceding expression or collection.


# Count input tokens through a separate API call before generating a summary.
def estimate_input_tokens(firm: dict) -> int:  # Estimate prompt tokens without generating a summary.
    """Estimate input tokens without generating a response."""
    counted = client.messages.count_tokens(  # Ask the provider to count prompt tokens without generating an answer.
        model=MODEL,  # Choose the model used for this request.
        system=SYSTEM_PROMPT,  # Supply the instructions that guide the model response.
        messages=[{"role": "user", "content": build_prompt(firm)}],  # Supply the user messages sent to the model.
    )  # Close the preceding expression or collection.
    return counted.input_tokens  # Return the estimated number of input tokens.


def stream_firm_summary(firm: dict):  # Generate a firm summary as a sequence of text chunks.
    """Yields text chunks as they arrive rather than waiting for the whole response."""
    with client.messages.stream(  # Open a model response stream that closes when this block finishes.
        model=MODEL,  # Choose the model used for this request.
        max_tokens=400,  # Set the maximum number of output tokens for this request.
        system=SYSTEM_PROMPT,  # Supply the instructions that guide the model response.
        messages=[{"role": "user", "content": build_prompt(firm)}],  # Supply the user messages sent to the model.
    ) as stream:  # Enter the streaming context and name the open stream.
        for text in stream.text_stream:  # Read each text chunk as the model produces it.
            yield text  # Pass the current chunk to the caller without waiting for the whole answer.

class FirmAnalysis(BaseModel):  # Define the validated fields for FirmAnalysis.
    """Define the required structure of a firm analysis."""

    tier: str = Field(description="One of: magic circle, national, boutique")  # Declare tier and apply the validation constraints or description shown here.
    strengths: list[str] = Field(max_length=3)  # Declare strengths and apply the validation constraints or description shown here.
    risks: list[str] = Field(max_length=3)  # Declare risks and apply the validation constraints or description shown here.
    headcount_efficiency: str = Field(description="high, medium or low")  # Declare headcount_efficiency and apply the validation constraints or description shown here.

def analyse_firm(firm: dict) -> dict:  # Generate an analysis matching the structured output schema.
    """structured output. the response is validated against FirmAnalysis ..... or it fails."""
    response = client.messages.parse(  # Send the model request and retain the provider response.
        model=MODEL,  # Choose the model used for this request.
        max_tokens=600,  # Set the maximum number of output tokens for this request.
        system = SYSTEM_PROMPT,  # Supply the instructions that guide the model response.
        messages=[{"role": "user", "content": build_prompt(firm)}],  # Supply the user messages sent to the model.
        output_format=FirmAnalysis,  # Require the generated output to follow the FirmAnalysis schema.

    )  # Close the preceding expression or collection.
    analysis = response.parsed_output  # Read the parsed result even when the first block is not text.
    if analysis is None:
        raise ValueError("The model did not return a structured analysis")

    return {  # Build and return a dictionary containing the following fields.



        "id": firm["id"],  # Include the record identifier in this record.
        "name": firm["name"],  # Include the name in this record.
        "analysis": analysis,  # Include the structured analysis in this record.
        "input_tokens": response.usage.input_tokens,  # Include the input token count in this record.
        "output_tokens": response.usage.output_tokens,  # Include the output token count in this record.
        "stop_reason": response.stop_reason,  # Include the reason generation stopped in this record.
    }  # Close the preceding expression or collection.



logger = logging.getLogger(__name__)  # Get a logger named after this module.


def call_anthropic_with_retry(  # Call the model with retries and log the estimated token cost.
    client,  # Accept the model client used to send requests.
    *,  # Require all following function arguments to be passed by name.
    model: str,  # Require a model name as a keyword argument.
    messages: list[dict],  # Require the conversation messages as a list of dictionaries.
    max_tokens: int = 500,  # Default the maximum generated output to 500 tokens.
    max_retries: int = 3,  # Default to three retries after the initial attempt.
    input_cost_per_million: float = 0.0,  # Accept the input price per million tokens, defaulting to zero.
    output_cost_per_million: float = 0.0,  # Accept the output price per million tokens, defaulting to zero.
):  # Close the preceding expression or collection.
    for attempt in range(max_retries + 1):  # Allow the initial request plus the configured number of retries.
        try:  # Attempt the following operations and handle the specified errors below.
            response = client.messages.create(  # Send the model request and retain the provider response.
                model=model,  # Choose the model used for this request.
                max_tokens=max_tokens,  # Set the maximum number of output tokens for this request.
                messages=messages,  # Supply the user messages sent to the model.
            )  # Close the preceding expression or collection.

            input_tokens = response.usage.input_tokens  # Read the number of input tokens used by the response.
            output_tokens = response.usage.output_tokens  # Read the number of output tokens produced by the response.

            cost = (  # Calculate the total estimated cost of input and output tokens.
                input_tokens / 1_000_000 * input_cost_per_million  # Calculate the input cost using the price per million tokens.
                + output_tokens / 1_000_000 * output_cost_per_million  # Add the output cost using the price per million tokens.
            )  # Close the preceding expression or collection.

            logger.info(  # Write the estimated request cost and token usage to the information log.
                "Anthropic call cost: $%.6f "  # Provide the log message template; placeholders are filled by the following arguments.
                "(input_tokens=%d, output_tokens=%d)",  # Provide the log message template; placeholders are filled by the following arguments.
                cost,  # Supply this value for the matching placeholder in the log message.
                input_tokens,  # Supply this value for the matching placeholder in the log message.
                output_tokens,  # Supply this value for the matching placeholder in the log message.
            )  # Close the preceding expression or collection.

            return response  # Return response to the caller.

        except (  # Handle the provider errors listed below so the request can be retried.
            anthropic.APITimeoutError,  # Include this provider exception among the retryable failures.
            anthropic.RateLimitError,  # Include this provider exception among the retryable failures.
            anthropic.APIConnectionError,  # Include this provider exception among the retryable failures.
        ):  # Close the preceding expression or collection.
            if attempt == max_retries:  # Check whether this was the final allowed attempt.
                raise  # Re-raise the current exception after all retries have been used.

            delay = 2 ** attempt  # Double the wait on each successive retry: 1, 2, 4 seconds, and so on.

            logger.warning(  # Log that the failed request will be retried after a delay.
                "Anthropic request failed. Retrying in %s seconds...",  # Provide the log message template; placeholders are filled by the following arguments.
                delay,  # Supply this value for the matching placeholder in the log message.
            )  # Close the preceding expression or collection.

            time.sleep(delay)  # Wait for the calculated number of seconds before retrying.



# import anthropic, inspect
#c = anthropic.Anthropic(api_key="anything")

# Does the method it called actually exist?
#print([m for m in dir(c.messages) if not m.startswith("_")])

# Does every parameter it used actually exist?
#print(list(inspect.signature(c.messages.create).parameters))

# Does every field it reads off the response actually exist?
#from anthropic.types import Message
#print(list(Message.model_fields))
