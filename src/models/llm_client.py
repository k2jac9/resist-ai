"""Nebius AI Studio LLM client for AMR-AI reasoning tasks.

Uses the available LLMs (DeepSeek-R1, Qwen3, etc.) for:
- Target analysis and interpretation
- Drug mechanism explanation
- Safety assessment reasoning
- Report generation
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Best models for reasoning tasks on Nebius
_REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528"
_FAST_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
_CODER_MODEL = "Qwen/Qwen2.5-Coder-7B-fast"


class NebisLLM:
    """Client for Nebius AI Studio LLM inference."""

    def __init__(self, model: str = _FAST_MODEL) -> None:
        self._model = model
        self._api_key = os.environ.get("NEBIUS_API_KEY", "")
        if not self._api_key:
            try:
                env_path = os.path.join(os.getcwd(), ".env")
                if os.path.exists(env_path):
                    for line in open(env_path):
                        if line.startswith("NEBIUS_API_KEY="):
                            self._api_key = line.split("=", 1)[1].strip()
            except Exception:
                pass
        self._client = None
        self._available = False
        self._init()

    def _init(self) -> None:
        if not self._api_key:
            logger.warning("No NEBIUS_API_KEY; LLM features disabled")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url="https://api.studio.nebius.com/v1/",
                api_key=self._api_key,
            )
            self._available = True
            logger.info("Nebius LLM client ready (model=%s)", self._model)
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
            if json_mode:
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
