"""LLM service for extraction and explanation workflows."""

import os
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

from hireintel_ai.core.config import get_settings


class LlmService:
    """Coordinate LLM-backed tasks without owning deterministic scoring."""

    def __init__(self):
        """Initialize LLM service with configuration."""
        self.settings = get_settings()
        self.api_key = self.settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = self.settings.base_url
        self.model = self.settings.model

    def is_configured(self) -> bool:
        """Return whether an LLM provider is configured.

        Returns:
            True if API key and model are configured.
        """
        return bool(self.api_key and self.model)

    def explain_candidate_score(
        self,
        candidate_a_name: str,
        candidate_b_name: str,
        score_a: float,
        score_b: float,
        components_a: list,
        components_b: list,
    ) -> str:
        """Generate an LLM explanation for why candidate A ranked above/below B.

        Args:
            candidate_a_name: Name of first candidate.
            candidate_b_name: Name of second candidate.
            score_a: Score of first candidate.
            score_b: Score of second candidate.
            components_a: Matched components for candidate A.
            components_b: Matched components for candidate B.

        Returns:
            LLM-generated explanation text.
        """
        if not self.is_configured():
            return self._fallback_explanation(
                candidate_a_name,
                candidate_b_name,
                score_a,
                score_b,
                components_a,
                components_b,
            )

        # Build context for LLM
        a_matched = sum(1 for c in components_a if c.get("matched"))
        b_matched = sum(1 for c in components_b if c.get("matched"))

        a_strengths = ", ".join([c.get("item_name", "Unknown") for c in components_a if c.get("matched")][:3])
        b_strengths = ", ".join([c.get("item_name", "Unknown") for c in components_b if c.get("matched")][:3])

        prompt = f"""You are a recruiter assistant. Analyze why one candidate scored higher than another and provide a clear, concise explanation.

Candidate A: {candidate_a_name}
- Score: {score_a:.1f}/100
- Matched Requirements: {a_matched}
- Top Strengths: {a_strengths if a_strengths else "None matched"}

Candidate B: {candidate_b_name}
- Score: {score_b:.1f}/100
- Matched Requirements: {b_matched}
- Top Strengths: {b_strengths if b_strengths else "None matched"}

Provide a 2-3 sentence explanation of why the candidate with the higher score ranked better. Focus on requirement matching and demonstrated strengths. Be objective and evidence-based."""

        try:
            return self._call_llm(prompt)
        except Exception as e:
            print(f"Warning: LLM call failed ({e}), using fallback explanation.")
            return self._fallback_explanation(
                candidate_a_name,
                candidate_b_name,
                score_a,
                score_b,
                components_a,
                components_b,
            )

    def _call_llm(self, prompt: str) -> str:
        """Call OpenRouter LLM API.

        Args:
            prompt: Prompt text to send to LLM.

        Returns:
            LLM response text.
        """
        if httpx is None:
            raise ImportError("httpx required for LLM calls; install with: pip install httpx")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/sandipan-ds/hireintel_ai",
            "X-Title": "HireIntel AI",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.7,
            "max_tokens": 300,
        }

        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

    def _fallback_explanation(
        self,
        candidate_a_name: str,
        candidate_b_name: str,
        score_a: float,
        score_b: float,
        components_a: list,
        components_b: list,
    ) -> str:
        """Fallback deterministic explanation when LLM not available.

        Args:
            candidate_a_name: Name of first candidate.
            candidate_b_name: Name of second candidate.
            score_a: Score of first candidate.
            score_b: Score of second candidate.
            components_a: Matched components for candidate A.
            components_b: Matched components for candidate B.

        Returns:
            Fallback explanation text.
        """
        a_matched = sum(1 for c in components_a if c.get("matched"))
        b_matched = sum(1 for c in components_b if c.get("matched"))

        if score_a > score_b:
            diff = score_a - score_b
            return f"{candidate_a_name} ranked higher by {diff:.1f} points with {a_matched} matched requirements vs {b_matched} for {candidate_b_name}."
        elif score_b > score_a:
            diff = score_b - score_a
            return f"{candidate_b_name} ranked higher by {diff:.1f} points with {b_matched} matched requirements vs {a_matched} for {candidate_a_name}."
        else:
            return f"Both candidates scored equally at {score_a:.1f} points. Consider other factors like cultural fit or growth potential."

