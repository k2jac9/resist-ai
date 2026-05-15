"""LLM client for AMR-AI reasoning tasks.

Supports multiple OpenAI-compatible providers via LLM_PROVIDER env var
(default: ollama — free local inference):
- ollama     (local Ollama — gemma4, llama, etc., no network, no cost)
- nebius     (Nebius AI Studio — DeepSeek-R1, Qwen3)
- openrouter (OpenRouter free tier — DeepSeek-R1, Qwen3, Llama)
- anthropic  (Anthropic Claude via OpenAI-compat endpoint)

Used for target analysis, drug mechanism, safety reasoning, report generation.
"""
from __future__ import annotations
import json, logging, os
from typing import Any

logger = logging.getLogger(__name__)

# Per-provider config: base URL, env var for key, default model.
# Keys:
#   base_url           — OpenAI-compatible endpoint (resolved lazily for ollama)
#   key_env            — env var holding the API key
#   default_model      — fallback if LLM_MODEL not set
#   supports_json_mode — whether response_format={"type":"json_object"} is accepted
#   requires_key       — whether an API key is mandatory (False for local ollama)
_PROVIDERS: dict[str, dict[str, Any]] = {
    "ollama": {
        "base_url": None,  # resolved from OLLAMA_BASE_URL env var, default below
        "key_env": "OLLAMA_API_KEY",
        "default_model": "gemma4:e4b",
        "supports_json_mode": True,
        "requires_key": False,
    },
    "nebius": {
        "base_url": "https://api.studio.nebius.com/v1/",
        "key_env": "NEBIUS_API_KEY",
        "default_model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "supports_json_mode": True,
        "requires_key": True,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "deepseek/deepseek-r1:free",
        "supports_json_mode": True,
        "requires_key": True,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/",
        "key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6",
        "supports_json_mode": False,  # Claude OAI-compat doesn't accept response_format
        "requires_key": True,
    },
}

_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"

# Legacy aliases kept for any external importers.
_REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528"
_FAST_MODEL = _PROVIDERS["nebius"]["default_model"]
_CODER_MODEL = "Qwen/Qwen2.5-Coder-7B-fast"


def _read_env_key(key_env: str) -> str:
    """Read a key from os.environ, falling back to parsing .env directly.

    The .env fallback preserves behavior for callers that import this module
    before python-dotenv has had a chance to populate os.environ.
    """
    val = os.environ.get(key_env, "")
    if val:
        return val
    try:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            prefix = f"{key_env}="
            for line in open(env_path):
                if line.startswith(prefix):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


class NebisLLM:
    """Provider-agnostic LLM client (class name kept for import compat)."""

    def __init__(self, model: str | None = None) -> None:
        self._provider = os.environ.get("LLM_PROVIDER", "ollama").lower().strip()
        if self._provider not in _PROVIDERS:
            logger.warning(
                "Unknown LLM_PROVIDER=%r; falling back to 'ollama'", self._provider
            )
            self._provider = "ollama"
        cfg = _PROVIDERS[self._provider]
        self._cfg = cfg
        self._model = model or os.environ.get("LLM_MODEL") or cfg["default_model"]
        self._base_url = self._resolve_base_url()
        self._api_key = _read_env_key(cfg["key_env"]) or ("ollama" if self._provider == "ollama" else "")
        self._client = None
        self._available = False
        self._init()

    def _resolve_base_url(self) -> str:
        """Return the base URL, honoring OLLAMA_BASE_URL for local provider."""
        if self._provider == "ollama":
            return os.environ.get("OLLAMA_BASE_URL", _OLLAMA_DEFAULT_BASE_URL).rstrip("/") + ("" if _OLLAMA_DEFAULT_BASE_URL.endswith("/") else "")
        return self._cfg["base_url"]

    def _init(self) -> None:
        if self._cfg.get("requires_key", True) and not self._api_key:
            logger.warning(
                "No %s set; LLM features disabled (provider=%s)",
                self._cfg["key_env"], self._provider,
            )
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key or "placeholder",
            )
            # For ollama, verify the server is actually reachable before marking available.
            if self._provider == "ollama":
                import httpx
                try:
                    httpx.get(self._base_url.rstrip("/v1") + "/api/tags", timeout=2.0)
                except Exception as e:
                    logger.warning(
                        "Ollama not reachable at %s (%s); set OLLAMA_BASE_URL or switch LLM_PROVIDER",
                        self._base_url, e,
                    )
                    return
            self._available = True
            logger.info(
                "LLM client ready (provider=%s, model=%s, base_url=%s)",
                self._provider, self._model, self._base_url,
            )
        except Exception as e:
            logger.warning("Failed to init LLM client: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def complete(self, prompt: str, system: str = "", max_tokens: int = 2048,
                 temperature: float = 0.3, json_mode: bool = False) -> str:
        if not self._available:
            return ""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode and self._cfg.get("supports_json_mode", False):
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return ""

    def complete_json(self, prompt: str, system: str = "",
                      max_tokens: int = 2048) -> dict | list | None:
        raw = self.complete(prompt, system, max_tokens, json_mode=True)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            return None

    def analyze_target(self, target_name: str, pathogen: str,
                       pdb_id: str = "", function: str = "") -> dict:
        prompt = f"""Analyze this antimicrobial resistance target for drug discovery:

Target: {target_name}
Pathogen: {pathogen}
PDB ID: {pdb_id}
Known function: {function}

Provide a JSON response with:
{{
  "druggability_assessment": "high/medium/low with reasoning",
  "binding_site_description": "description of the active site",
  "known_inhibitors": ["list of known inhibitor classes"],
  "resistance_mechanism": "how this target contributes to resistance",
  "therapeutic_strategy": "recommended approach to target this protein",
  "clinical_relevance": "why this target matters clinically",
  "confidence": 0.0-1.0
}}"""
        system = ("You are an expert computational biologist specializing in "
                  "antimicrobial resistance and drug discovery. Respond with valid JSON only.")
        result = self.complete_json(prompt, system)
        return result or {"error": "LLM analysis unavailable", "target": target_name}

    def analyze_drug_candidate(self, drug_name: str, smiles: str,
                                target_name: str, binding_score: float) -> dict:
        prompt = f"""Analyze this drug repurposing candidate for antimicrobial activity:

Drug: {drug_name}
SMILES: {smiles}
Target: {target_name}
Predicted binding affinity: {binding_score:.3f}

Provide a JSON response with:
{{
  "mechanism_of_action": "how this drug works against the target",
  "repurposing_rationale": "why this existing drug could work for AMR",
  "strengths": ["list of advantages"],
  "risks": ["list of potential issues"],
  "clinical_precedent": "any existing clinical evidence",
  "development_recommendation": "next steps for development",
  "regulatory_pathway": "505(b)(2) or other applicable pathway",
  "estimated_timeline": "years to potential approval"
}}"""
        system = ("You are a pharmaceutical scientist specializing in drug repurposing "
                  "for antimicrobial resistance. Respond with valid JSON only.")
        result = self.complete_json(prompt, system)
        return result or {"error": "LLM analysis unavailable", "drug": drug_name}

    def generate_safety_interpretation(self, drug_name: str, smiles: str,
                                        admet_data: dict) -> str:
        prompt = f"""Interpret this ADMET safety profile for a clinician audience:

Drug: {drug_name}
SMILES: {smiles}
ADMET Data: {json.dumps(admet_data, indent=2)}

Write a 3-4 sentence plain-English safety summary that a non-scientist can understand.
Include specific risks to watch for and an overall safety verdict."""
        system = "You are a clinical pharmacologist explaining drug safety to a medical team."
        return self.complete(prompt, system, max_tokens=500)

    def generate_executive_report(self, pathogen: str, targets: list,
                                   candidates: list, num_screened: int) -> str:
        prompt = f"""Write a concise executive summary for an AI drug discovery pipeline run:

Pathogen: {pathogen}
Targets identified: {len(targets)} ({', '.join(t.get('name', t) if isinstance(t, dict) else str(t) for t in targets[:5])})
Compounds screened: {num_screened}
Top candidates: {json.dumps(candidates[:5], indent=2, default=str)}

Write a 2-paragraph executive summary suitable for hackathon judges.
Focus on: clinical impact, speed vs traditional methods, regulatory pathway, next steps.
Be specific about the pathogen threat and why these candidates matter."""
        system = ("You are a biotech venture analyst writing for hackathon judges "
                  "who include both scientists and business strategists.")
        return self.complete(prompt, system, max_tokens=800)
