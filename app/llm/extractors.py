import json
from app.models.booking import ExtractionResult, get_extract_booking_tool
from app.llm.client import client


def llm_extract_email(email_text: str) -> ExtractionResult:
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

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": email_text},
        ],
        tools=[tool],
        tool_choice="auto",
        temperature=0,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)

    return ExtractionResult(**args)
