import json
import os
from pathlib import Path
from typing import Any

import httpx
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import APIError
from pydantic import BaseModel, Field

load_dotenv(override=True)


app = FastAPI(
    title="Financial Research Agent",
    version="0.1.0",
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna",
)


OLOSTEP_URL = "https://api.olostep.com/v1"

# Research input
class ResearchRequest(BaseModel):
    company : str = Field(
        min_length=1,
        max_length=200,
    )

    period : str = Field(
        default= "6 months",
        min_length= 1,
        max_length=100,
    )

    focus : str = Field(
        default="Full company research",
        min_length=1,
        max_length=1000,
    )

# Sending a request to Olostep

async def olostep(
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:

    api_key = os.getenv("OLOSTEP_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OLOSTEP_API_KEY is not configured"
        )

    async with httpx.AsyncClient(
        timeout=45
    ) as client:

        response = await client.post(
            f"{OLOSTEP_URL}{path}",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
        )

        response.raise_for_status()

        return response.json()

# First tool to allow agent to search the web from OpenAI Agents SDK

@function_tool
async def search_web(query: str) -> str:
    """Search the live web for company research."""

    data = await olostep(
        "/searches",
        {
            "query": query,
            "limit": 5,
        },
    )

    return json.dumps(
        data.get(
            "result",
            {},
        ).get(
            "links",
            [],
        )
    )

# Second tool to read the sources

@function_tool
async def read_source(url: str) -> str:
    """Read an important source found during research."""

    data = await olostep(
        "/scrapes",
        {
            "url_to_scrape": url,
            "formats": ["markdown"],
            "remove_images": True,
        },
    )

    return (
        data.get("result", {})
        .get("markdown_content", "")
    )[:15000]


## CREATING A FINANCIAL RESEARCH AGENT

research_agent = Agent(
    name="Financial Research Analyst",

    model=MODEL,

    instructions="""
    Research the public company provided by the user.

    Investigate its business, recent financial
    performance, latest earnings and guidance,
    major developments during the requested period,
    competitors, risks, and potential catalysts.

    Prioritize investor-relations pages, regulatory
    filings, earnings releases, and reputable
    financial publications.

    Verify important figures, separate facts from
    interpretation, and include source URLs.

    Return a concise, structured report.

    Do not provide personalized investment advice.
    """,

    tools=[
        search_web,
        read_source,
    ],
)

## RUN THE AGENT

async def run_research(
    request: ResearchRequest,
) -> str:

    prompt = f"""
    Company: {request.company.strip()}
    Research period: {request.period.strip()}
    Focus: {request.focus.strip()}

    Research the company and produce a concise
    financial research report.
    """

    result = await Runner.run(
        research_agent,
        prompt,
        max_turns=12,
    )

    return str(result.final_output)

## Create the research API

@app.post("/research")
async def research(
    request: ResearchRequest,
) -> dict[str, str]:

    if (
        not os.getenv("OPENAI_API_KEY")
        or not os.getenv("OLOSTEP_API_KEY")
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Set OPENAI_API_KEY and "
                "OLOSTEP_API_KEY before "
                "running research."
            ),
        )

    try:
        report = await run_research(request)

    except (
        APIError,
        httpx.HTTPError,
        RuntimeError,
    ) as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                f"Research service failed: {exc}"
            ),
        ) from exc

    return {
        "company": request.company.strip(),
        "report": report,
    }

## Serve the Web application

@app.get(
    "/",
    response_class=FileResponse,
)
async def home() -> FileResponse:

    return FileResponse(
        STATIC_DIR / "index.html"
    )
