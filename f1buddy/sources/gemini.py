"""Optional AI analysis of a telemetry plot (Google Gemini)."""
import asyncio

from .. import ctx
from ..errors import SourceError

PROMPT = (
    "Analyze this image as if you are an F1 Race Engineer. Do not dumb things down and do not be afraid to use "
    "F1 lingo, you can assume the reader is familiar with F1 terms. It is a graph showcasing the car telemetry "
    "during the F1 {context}. The number of drivers in the graph is given in the legend. If there is more than "
    "one driver, give insights to the drivers styles and the different team's car performance. Otherwise provide "
    "insight on the single driver's performance and car around the lap. Keep it under 300 words."
)


def available() -> bool:
    return bool(ctx.config.gemini_key)


def _analyse(png: bytes, context: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=ctx.config.gemini_key)
    response = client.models.generate_content(
        model=ctx.config.gemini_model,
        contents=[types.Part.from_bytes(data=png, mime_type="image/png"), PROMPT.format(context=context)])
    return response.text or ""


async def analyse_telemetry(png: bytes, context: str) -> str:
    try:
        text = await asyncio.to_thread(_analyse, png, context)
    except Exception as e:
        raise SourceError("Gemini", f"{type(e).__name__}: {e}") from e
    if not text.strip():
        raise SourceError("Gemini", "empty response")
    return text.strip()
