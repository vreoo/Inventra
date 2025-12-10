import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests


logger = logging.getLogger(__name__)


class HuggingFaceError(Exception):
    """Base error raised when the Hugging Face API returns an error."""


class HuggingFaceRateLimit(HuggingFaceError):
    """Raised when a 429 rate limit response is encountered."""


@dataclass
class AiSummary:
    summary: str
    actions: List[str]
    risks: List[str]
    source: str
    generated_at: datetime


class PromptBuilder:
    """Create concise prompts for the AI summary model."""

    def build(self, metrics: Dict[str, Any]) -> str:
        logger.debug(
            "Building AI summary prompt from metrics: sku=%s mode=%s insights=%s",
            metrics.get("sku") or metrics.get("product_id") or "unknown",
            metrics.get("mode"),
            len(metrics.get("insights") or []),
        )
        insights = metrics.get("insights") or []
        normalized_insights = [
            str(message).strip() for message in insights if str(message).strip()
        ]
        if not normalized_insights:
            insight_block = "None"
        else:
            truncated = normalized_insights[:10]
            insight_block = "\n".join(f"- {item}"[:200] for item in truncated)

        prompt = (
            "You are an inventory planning assistant. Summarise the supply posture for one SKU.\n\n"
            f"SKU: {metrics.get('sku') or 'Unknown'}\n"
            f"Mode: {metrics.get('mode') or 'inventory'}\n"
            f"Forecast horizon (days): {metrics.get('horizon') or 'unknown'}\n"
            f"Projected stockout date: {metrics.get('stockout_date') or 'none'}\n"
            f"Reorder point (units): {self._safe_number(metrics.get('reorder_point'))}\n"
            f"Recommended reorder date: {metrics.get('reorder_date') or 'tbd'}\n"
            f"Recommended order quantity (units): {self._safe_number(metrics.get('recommended_order_qty'))}\n"
            f"Safety stock (units): {self._safe_number(metrics.get('safety_stock'))}\n"
            f"Service level target: {self._format_percentage(metrics.get('service_level'))}\n"
            "Key model insights:\n"
            f"{insight_block}\n\n"
            "Respond in JSON with keys `summary`, `actions` (array), `risks` (array). "
            "Keep sentences short, avoid jargon, and reference the SKU name once."
        )
        return prompt[:6000]

    def _safe_number(self, value: Any) -> str:
        if value is None:
            return "unknown"
        try:
            if isinstance(value, (int, float)) and not math.isnan(value):
                return f"{value:.2f}"
        except (TypeError, ValueError):
            pass
        return str(value)

    def _format_percentage(self, value: Any) -> str:
        if value is None:
            return "unknown"
        try:
            numeric = float(value)
            if 0 <= numeric <= 1:
                return f"{numeric * 100:.1f}%"
            return f"{numeric:.1f}%"
        except (TypeError, ValueError):
            return str(value)


class HuggingFaceClient:
    """Lightweight client for Hugging Face Chat Completions API."""

    def __init__(
        self,
        api_token: str,
        model: str,
        timeout_seconds: float = 20.0,
        base_url: str | None = None,
    ):
        self.model = model
        base = base_url or "https://router.huggingface.co/v1/chat/completions"
        self.url = base.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }
        self.timeout = timeout_seconds
        self.session = requests.Session()

    def generate(self, prompt: str) -> Any:
        start_time = time.monotonic()
        logger.info(
            "Dispatching AI summary request (model=%s, url=%s, prompt_chars=%d)",
            self.model,
            self.url,
            len(prompt),
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an inventory planning assistant that writes concise, structured updates."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "temperature": 0.1,
        }
        response = self.session.post(
            self.url,
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code == 429:
            raise HuggingFaceRateLimit("Rate limit encountered")

        if response.status_code >= 400:
            detail = response.text[:500]
            raise HuggingFaceError(f"API error {response.status_code}: {detail}")

        elapsed = time.monotonic() - start_time
        logger.info(
            "AI summary response received (status=%s, elapsed=%.2fs)",
            response.status_code,
            elapsed,
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("AI summary raw response text: %s", response.text[:1000])

        return response.json()


class AiSummaryService:
    """Orchestrates prompt construction, caching, and response parsing."""

    def __init__(
        self,
        api_token: str,
        model: str = "HuggingFaceH4/zephyr-7b-beta",
        enable_cache: bool = True,
        max_retries: int = 2,
        backoff_seconds: float = 2.0,
        base_url: str | None = None,
        fallback_models: Optional[List[str]] = None,
    ):
        self.primary_model = model
        self.models_to_try: List[str] = [model] + [
            candidate
            for candidate in (fallback_models or [])
            if candidate and candidate != model
        ]
        self._api_token = api_token
        self._base_url = base_url
        self.prompt_builder = PromptBuilder()
        self._clients: Dict[str, HuggingFaceClient] = {}
        self.enable_cache = enable_cache
        self.cache: Dict[Tuple[str, str], AiSummary] = {}
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        logger.info(
            "AI summary service configured with model candidates: %s",
            ", ".join(self.models_to_try),
        )

    def _get_client(self, model: str) -> HuggingFaceClient:
        if model not in self._clients:
            self._clients[model] = HuggingFaceClient(
                api_token=self._api_token,
                model=model,
                base_url=self._base_url,
            )
        return self._clients[model]

    def summarize(self, job_id: str, metrics: Dict[str, Any]) -> AiSummary:
        sku = str(metrics.get("sku") or metrics.get("product_id") or "unknown")
        logger.info(
            "AI summary requested (job_id=%s, sku=%s, cache_enabled=%s)",
            job_id,
            sku,
            self.enable_cache,
        )
        cache_key = (job_id, sku)
        if self.enable_cache and cache_key in self.cache:
            logger.info("Returning cached AI summary (job_id=%s, sku=%s)", job_id, sku)
            return self.cache[cache_key]

        prompt = self.prompt_builder.build(metrics)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "AI summary prompt prepared (job_id=%s, sku=%s): %s",
                job_id,
                sku,
                prompt,
            )

        summary: Optional[AiSummary] = None
        used_model: Optional[str] = None
        for model_index, model_name in enumerate(self.models_to_try):
            client = self._get_client(model_name)
            logger.info(
                "Attempting AI summary with model '%s' (%d/%d)",
                model_name,
                model_index + 1,
                len(self.models_to_try),
            )
            model_succeeded = False
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info(
                        "AI summary attempt %d/%d (job_id=%s, sku=%s, model=%s)",
                        attempt + 1,
                        self.max_retries + 1,
                        job_id,
                        sku,
                        model_name,
                    )
                    raw_response = client.generate(prompt)
                    logger.debug(
                        "AI summary raw response object (job_id=%s, sku=%s, model=%s): %s",
                        job_id,
                        sku,
                        model_name,
                        repr(raw_response)[:1000],
                    )
                    summary = self._parse_response(raw_response, sku, model_name)
                    if summary:
                        used_model = model_name
                        model_succeeded = True
                        break
                    logger.warning(
                        "AI summary response could not be parsed for %s (model=%s); trying next model",
                        sku,
                        model_name,
                    )
                    summary = None
                    break
                except HuggingFaceRateLimit as err:
                    if attempt >= self.max_retries:
                        logger.warning(
                            "AI summary rate limited for %s (model=%s): %s",
                            sku,
                            model_name,
                            err,
                        )
                        break
                    sleep_for = self.backoff_seconds * (2 ** attempt)
                    logger.info(
                        "AI summary rate limited for %s (model=%s), retrying in %.1fs (attempt %d)",
                        sku,
                        model_name,
                        sleep_for,
                        attempt + 1,
                    )
                    time.sleep(sleep_for)
                except HuggingFaceError as err:
                    error_text = str(err)
                    if "model_not_supported" in error_text:
                        logger.error(
                            "AI summary model '%s' is not enabled for the current Hugging Face token; "
                            "update AI_SUMMARY_MODEL or enable the provider on your Hugging Face account.",
                            model_name,
                        )
                        break
                    logger.warning(
                        "AI summary request failed for %s (model=%s): %s",
                        sku,
                        model_name,
                        err,
                    )
                    break
                except Exception as err:  # pragma: no cover - defensive
                    logger.exception(
                        "Unexpected AI summary error for %s (model=%s): %s",
                        sku,
                        model_name,
                        err,
                    )
                    break
            if summary:
                break
            if not model_succeeded:
                logger.info(
                    "AI summary model '%s' did not produce a result for %s; continuing to next candidate",
                    model_name,
                    sku,
                )

        if not summary:
            logger.info(
                "Falling back to deterministic summary (job_id=%s, sku=%s)", job_id, sku
            )
            model_for_fallback = used_model or self.primary_model
            summary = self._fallback_summary(metrics, sku, model_for_fallback)
        else:
            logger.info(
                "AI summary parsed successfully (job_id=%s, sku=%s, source=%s)",
                job_id,
                sku,
                summary.source,
            )

        if self.enable_cache:
            self.cache[cache_key] = summary
            logger.debug(
                "AI summary cached (job_id=%s, sku=%s, source=%s, expires=process lifetime)",
                job_id,
                sku,
                summary.source,
            )

        return summary

    def _parse_response(self, response: Any, sku: str, source: str) -> Optional[AiSummary]:
        """
        Handle the variety of shapes returned by the inference API.
        """
        candidate_text: Optional[str] = None
        logger.debug("Parsing AI summary response for sku=%s: %s", sku, type(response))

        if isinstance(response, list) and response:
            first = response[0]
            if isinstance(first, dict):
                candidate_text = first.get("generated_text")
            elif isinstance(first, str):
                candidate_text = first
        elif isinstance(response, dict):
            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                candidate_text = message.get("content")
            if not candidate_text:
                candidate_text = response.get("generated_text") or response.get("data")
        elif isinstance(response, str):
            candidate_text = response

        if not candidate_text:
            logger.warning("AI summary response missing text payload for sku=%s", sku)
            return None

        parsed = self._extract_payload(candidate_text)
        if not parsed:
            logger.warning(
                "AI summary JSON payload could not be extracted for sku=%s", sku
            )
            return None

        return AiSummary(
            summary=parsed["summary"],
            actions=parsed.get("actions") or [],
            risks=parsed.get("risks") or [],
            source=source,
            generated_at=datetime.now(timezone.utc),
        )

    def _extract_payload(self, text: str) -> Optional[Dict[str, Any]]:
        cleaned = text.strip()
        if not cleaned:
            logger.debug("AI summary candidate text empty after strip")
            return None

        # Some inference responses include extra text before/after the JSON blob.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.debug("AI summary payload missing JSON braces: %s", cleaned[:200])
            return None

        candidate = cleaned[start : end + 1]
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            logger.debug("AI summary payload JSON decode failure: %s", candidate[:200])
            return None

        if not isinstance(payload, dict):
            logger.debug("AI summary payload not a dict: %s", type(payload))
            return None

        summary_text = self._normalise_summary(payload.get("summary"), payload)
        if not summary_text:
            logger.debug("AI summary payload missing usable summary field")
            return None

        actions = self._normalise_items(payload.get("actions"))
        risks = self._normalise_items(payload.get("risks"))

        return {
            "summary": summary_text,
            "actions": actions,
            "risks": risks,
        }

    def _normalise_summary(
        self, summary_field: Any, payload: Dict[str, Any]
    ) -> Optional[str]:
        if summary_field is None:
            return None

        if isinstance(summary_field, str):
            text = summary_field.strip()
            return text or None

        if isinstance(summary_field, dict):
            if isinstance(summary_field.get("text"), str):
                text = summary_field["text"].strip()
                if text:
                    return text

            parts: List[str] = []
            for key, value in summary_field.items():
                formatted = self._format_value(value)
                if not formatted:
                    continue
                label = key.replace("_", " ").capitalize()
                parts.append(f"{label}: {formatted}")

            combined = "; ".join(parts)
            if combined:
                return combined

        if isinstance(summary_field, list):
            items = [
                self._format_value(item)
                for item in summary_field
                if self._format_value(item)
            ]
            if items:
                return "; ".join(items)

        return self._format_value(summary_field)

    def _normalise_items(self, items: Any) -> List[str]:
        normalised: List[str] = []
        if isinstance(items, list):
            for item in items:
                formatted = self._format_item(item)
                if formatted:
                    normalised.append(formatted)
        elif isinstance(items, dict):
            formatted = self._format_item(items)
            if formatted:
                normalised.append(formatted)
        elif items is not None:
            formatted = self._format_value(items)
            if formatted:
                normalised.append(formatted)
        return normalised

    def _format_item(self, item: Any) -> Optional[str]:
        if isinstance(item, str):
            text = item.strip()
            return text or None

        if isinstance(item, dict):
            if isinstance(item.get("text"), str):
                text = item["text"].strip()
                if text:
                    return text

            segments: List[str] = []
            for key, value in item.items():
                formatted = self._format_value(value)
                if not formatted:
                    continue
                cleaned_key = key.replace("_", " ").capitalize()
                if key in {"action", "risk", "message"}:
                    segments.append(formatted)
                else:
                    segments.append(f"{cleaned_key}: {formatted}")

            combined = "; ".join(segments)
            return combined or None

        return self._format_value(item)

    @staticmethod
    def _format_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, (int,)):
            return str(value)
        if isinstance(value, float):
            if math.isnan(value):
                return None
            return f"{value:.2f}"
        return str(value).strip() or None

    def _fallback_summary(
        self, metrics: Dict[str, Any], sku: str, model_name: str
    ) -> AiSummary:
        recommended_qty = metrics.get("recommended_order_qty")
        reorder_date = metrics.get("reorder_date")
        stockout_date = metrics.get("stockout_date")

        parts = [f"Inventory summary for {sku} is unavailable."]
        if stockout_date:
            parts.append(f"Projected stockout: {stockout_date}.")
        if reorder_date:
            parts.append(f"Plan reorder by {reorder_date}.")
        if recommended_qty:
            try:
                qty = float(recommended_qty)
                parts.append(f"Suggested order quantity: {qty:.0f} units.")
            except (TypeError, ValueError):
                parts.append(f"Suggested order quantity: {recommended_qty}.")

        summary = " ".join(parts)
        actions: List[str] = []
        if reorder_date:
            actions.append(f"Schedule procurement for {reorder_date}.")
        if recommended_qty:
            actions.append(f"Review order volume near {recommended_qty}.")

        risks = []
        if stockout_date:
            risks.append(f"Possible stockout on {stockout_date}.")

        return AiSummary(
            summary=summary,
            actions=actions,
            risks=risks,
            source=f"{model_name}-fallback",
            generated_at=datetime.now(timezone.utc),
        )
