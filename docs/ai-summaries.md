# AI Forecast Summaries

## Overview

The AI summary pipeline augments completed forecast jobs with concise narratives,
recommended actions, and key risks per SKU. Summaries are generated with the
`HuggingFaceH4/zephyr-7b-beta` hosted model via the Hugging Face Inference API.
When the integration is disabled or unavailable, the backend falls back to
standard numeric results so existing workflows continue to operate.

## Setup

1. Create a free Hugging Face account and generate a personal access token with
   Inference permissions: https://huggingface.co/settings/tokens  
2. Add the following environment variables to `backend/.env` (or your process
   manager configuration):

   ```
   ENABLE_AI_SUMMARY=true
   HF_API_TOKEN=hf_xxx_your_token_here
   AI_SUMMARY_MODEL=HuggingFaceH4/zephyr-7b-beta
   # Optional override if self-hosting: HF_API_BASE_URL=https://router.huggingface.co/v1/chat/completions
   ```

3. Restart the FastAPI server. Use `curl http://localhost:8000/api/ai/status` to
   confirm the feature is enabled.

## Usage

- When `ENABLE_AI_SUMMARY` is true and `HF_API_TOKEN` is present, background job
  processing requests the model once per `{jobId, sku}` and stores the structured
  results on each `ForecastResult`.
- The frontend renders the narrative inside the forecast results view. If AI
  summaries are enabled but a particular SKU is missing a response, the UI shows
  a non-blocking warning so planners fall back to numeric insights.
- Job configuration can opt-in on a per-run basis with
  `config.enable_ai_summary = true`. The effective toggle is
  `ENABLE_AI_SUMMARY` **and** `config.enable_ai_summary`; if the env flag is off,
  per-run overrides are ignored for safety.

## Troubleshooting

- **429 Rate Limit** — The service retries twice with exponential backoff. If the
  limit persists, the backend records a fallback summary; consider lowering job
  volume or upgrading the Hugging Face plan.
- **Invalid JSON Responses** — The chat completion endpoint occasionally returns plain
  text. The backend validates the payload and falls back gracefully; check the
  server logs for `AI summary` warnings to inspect raw outputs.
- **Missing Token** — The `/api/ai/status` endpoint returns `enabled: false` when
  the token is missing or blank. Ensure the environment reloads after updating
  secrets. Do not commit personal tokens to the repository.

## Security Notes

- Forecast payloads include SKU names, inventory posture, and supporting
  insights. Verify that sending this data to Hugging Face complies with your data
  handling policies.
- Rotate the Hugging Face token regularly and scope it to inference-only access.
  Never embed the token in frontend bundles or share it in logs.
