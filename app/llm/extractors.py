import json
from app.models.booking import ExtractionResult, get_extract_booking_tool
from app.llm.client import client
import logfire

logfire.configure()


def llm_extract_email(email_text: str) -> ExtractionResult:
    with logfire.span("llm_extract_email", email_length=len(email_text)):
        tool = get_extract_booking_tool()
        prompt = """
    You are an email parsing assistant.

    The user will send you RAW email text (headers, HTML, bodies, weird formatting)
    representing either a booking (hotel, car, plane, train, tour, etc) OR a marketing email

    Your job:
    1. Determine if this is a BOOKING email or MARKETING email.
    2. If booking, extract all booking details.
    3. If marketing, set kind="marketing" and booking=null.

    OUTPUT:
    Use the extract_booking tool.
        """.strip()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=prompt,
            messages=[
                {"role": "user", "content": email_text},
            ],
            tools=[tool],
            tool_choice={"type": "tool", "name": "extract_booking"},
        )
        logfire.info("LLM response", stop_reason=response.stop_reason)

        # Extract tool use result from response content blocks
        for block in response.content:
            if block.type == "tool_use":
                logfire.info("LLM tool_use", tool_input=block.input)
                return ExtractionResult(**block.input)

        raise ValueError("No tool_use block found in Claude response")
