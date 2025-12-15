# AI Forecast Summaries Implementation Plan

## 1. Objective

- Deliver human-friendly narratives for forecast outputs so non-expert planners can make decisions without interpreting raw numerics.
- Integrate the hosted `HuggingFaceH4/zephyr-7b-beta` model via Hugging Face Inference API (free-tier) without using local models or paid APIs.
- Ensure the system degrades gracefully when the AI endpoint is unavailable or rate-limited.

## 2. Scope & Success Criteria

- **In scope**: Backend summariser service, API wiring, result model updates, feature flag, frontend rendering, documentation, unit/integration tests, basic health reporting.
- **Out of scope**: UI redesign beyond the AI card, advanced conversation/history, alternative providers, local LLM execution.
- **Done when**:
  1. A completed job supports on-demand AI summary generation per SKU and persists the response.
  2. Frontend renders the summary card and hides it gracefully when disabled/missing.
  3. Documentation covers setup and operational guidance, and automated tests verify success and fallback paths.

## 3. Architecture Overview

- **Model**: `HuggingFaceH4/zephyr-7b-beta` on `https://huggingface.co/HuggingFaceH4/zephyr-7b-beta`.
- **Inference Flow**:
  1. `POST /api/forecast/{job_id}/ai-summary` accepts a SKU/product id after the job completes.
  2. The handler loads stored results, assembles per-SKU metrics, and calls `AiSummaryService` using `HF_API_TOKEN`.
  3. Response is mapped into new fields on `ForecastResult` (summary, recommended actions, risks) and persisted back to the job file.
  4. The frontend fetches the updated job payload or uses the response to render the card immediately.
- **Configuration**:
  - `ENABLE_AI_SUMMARY` (default `false`) to gate the feature.
  - `HF_API_TOKEN` for authentication.
  - `AI_SUMMARY_MODEL` defaulting to the Zephyr endpoint (allow overrides for future providers).
- **Caching & Resilience**:

  - Per `{jobId, SKU}` memoisation in-memory to avoid duplicate requests on the same process run.
  - Respect 429 responses with exponential backoff (max 2 retries) and fallback to template text.

- **Config Exaple**:

```python
import os
import requests

API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.environ['HF_TOKEN']}",
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

response = query({
    "messages": [
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],
    "model": "HuggingFaceH4/zephyr-7b-beta:featherless-ai"
})

print(response["choices"][0]["message"])
```

## 4. Backend Work Breakdown

1. **Models (`backend/models/forecast.py`)**

   - Extend `ForecastResult` with:
     - `ai_summary: Optional[str]`
     - `ai_actions: Optional[list[str]]`
     - `ai_risks: Optional[list[str]]`
     - `ai_source: Optional[str] = "huggingface/zephyr-7b-beta"`
     - `ai_generated_at: Optional[datetime]`
   - Update Pydantic configs to allow these fields.

2. **Service Layer (`backend/services/ai_summarizer.py`)**

   - Create module with:
     - `PromptBuilder` that accepts metrics dict and produces concise prompt (≤ 800 tokens).
     - `HuggingFaceClient` handling HTTP POST, headers, retry, timeout (20s).
     - `Summarizer` orchestrating prompt creation, caching, and response parsing.
   - Response schema expectation:
     ```json
     [
       {
         "generated_text": "A concise narrative with bullet cues…"
       }
     ]
     ```
   - Parse narrative into:
     - `summary` (first paragraph).
     - `actions` (bullet lines starting with imperatives).
     - `risks` (lines flagged with "Risk" or "Watch").

3. **API Wiring (`backend/api/forecast.py`)**

   - Inject summariser into module scope (lazy init to avoid startup failures).
   - Add `POST /api/forecast/{job_id}/ai-summary` to call the summariser for a single SKU after the job completes.
   - Persist generated text + structured fields; on exception, return a 502 and leave existing data untouched.

4. **Configuration & Startup**
   - Update `backend/main.py` to read new env vars and expose `/api/ai/status` returning `{"enabled": bool, "model": str}`.
   - Add default env values in `.env.example`.
   - Ensure `requirements.txt` includes `requests` (already present via FastAPI stack) and no additional heavy deps.

## 5. Frontend Work Breakdown

1. **Type Updates (`frontend/src/services/api.ts`)**

   - Extend `ForecastSeries` with `ai_summary`, `ai_actions`, `ai_risks`, `ai_source`, `ai_generated_at`.

2. **Results Page (`frontend/src/app/results/page.tsx`)**

   - Replace placeholder AI sections with conditional rendering:
     - Summary paragraph.
     - Actions as bullet list.
     - Risks highlighted (yellow tone).
   - Show subtle badge with `ai_source` and generated timestamp.
   - If fields missing and job config indicates AI enabled, show “AI explanation unavailable” notice.

3. **Optional Interactions**
   - Add button with optimistic UI update tied to the on-demand endpoint.
   - Surface summaries through a dedicated `AiSummaryCard` component; retire legacy AI analysis panels that duplicated this information.

## 6. Prompt Template Draft

```
You are an inventory planning assistant. Summarise the supply posture for one SKU.

SKU: {sku}
Mode: {mode}
Forecast horizon (days): {horizon}
Projected stockout date: {stockout_date or "none"}
Reorder point (units): {reorder_point}
Recommended reorder date: {reorder_date or "tbd"}
Recommended order quantity (units): {recommended_order_qty}
Safety stock (units): {safety_stock}
Service level target: {service_level}
Key model insights:
{bullet list from insights or "None"}

Respond in JSON with keys `summary`, `actions` (array), `risks` (array). Keep sentences short, avoid jargon, reference the SKU name once. Assume reader is a supply planner.
```

- Post-process to ensure valid JSON; if generation returns plain text, fall back to heuristic parsing.

## 7. Testing Strategy

- **Unit Tests** (`backend/tests`):
  - Mock Hugging Face response and assert summariser parses narrative correctly.
  - Toggle `ENABLE_AI_SUMMARY` and confirm `ForecastJob` output includes/omits AI fields.
  - Simulate 429/timeout to verify graceful fallback.
- **Integration Smoke**:
  - Create local job fixture, inject fake summariser, and ensure `/api/forecast/{job_id}` returns AI fields.
- **Frontend Tests**:
  - Add React Testing Library test ensuring AI card renders summary/actions/risks and hides when absent.

## 8. Operational Considerations

- Cache tokens per process; respect Hugging Face rate limits (document ~30 RPM / 200k tokens/day).
- Log latency and error types to `app.log`.
- Provide clear messaging in README/docs about data sent to external service (PII, sensitive info).
- Monitor `.env` misconfiguration and surface actionable error messages in server logs.

## 9. Documentation & Handoff

- Create `docs/ai-summaries.md` (or extend this file) with:
  - Setup instructions (sign up, token creation steps with screenshots/links).
  - Environment variable descriptions.
  - Troubleshooting (common HTTP codes, quota exhaustion, JSON parse errors).
  - Security note on not committing tokens.
- Update `AGENTS.md` “Configuration & Feature Flags” to mention AI summary toggles.

## 10. Implementation Checklist

1. Add model fields & typings.
2. Implement summariser service + env handling.
3. Wire backend summary generation with fallback.
4. Update frontend rendering + tests.
5. Document setup & update contributor guide.
6. Manual QA: run sample job, verify summary, test disabled state.
7. Obtain review sign-off.
