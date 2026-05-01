from dataclasses import dataclass
import re


@dataclass
class AgentResult:
    agent_name: str
    content: str


class BaseAgent:
    name = "base"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        raise NotImplementedError


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower()))


def _summary_preview(text: str, max_chars: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return "No summary available"
    if len(compact) <= max_chars:
        return compact

    window = compact[:max_chars]
    cut_points = [window.rfind(sep) for sep in (". ", "? ", "! ", "; ")]
    cut = max(cut_points)
    if cut >= 80:
        return window[: cut + 1].strip()

    word_cut = window.rfind(" ")
    if word_cut >= 80:
        return window[:word_cut].strip() + "..."
    return window.strip() + "..."


def _find_clause_signals(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "set_aside_signal": any(term in lowered for term in ("set-aside", "small business", "8(a)", "hubzone", "sdvosb", "wosb")),
        "naics_signal": "naics" in lowered,
        "vehicle_signal": any(term in lowered for term in ("contract vehicle", "idiq", "bpa", "schedule", "gwac")),
        "evaluation_signal": any(term in lowered for term in ("evaluation", "factor", "section m", "tradeoff", "lpta", "best value")),
        "past_performance_signal": any(term in lowered for term in ("past performance", "cpars", "references", "recency", "relevancy")),
        "staffing_signal": any(term in lowered for term in ("key personnel", "resume", "staffing", "labor category", "fte", "hours")),
        "transition_signal": any(term in lowered for term in ("transition", "mobilization", "phase-in", "days after award", "start-up")),
        "pricing_signal": any(term in lowered for term in ("price", "cost", "ige", "ceiling", "nte", "cost realism", "wage determination")),
        "incumbent_signal": "incumbent" in lowered,
    }


def _detect_section_heading(text: str) -> str | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        md_match = re.match(r"^#{1,6}\s+(.+)$", line)
        if md_match:
            return md_match.group(1).strip()

        numbered_match = re.match(r"^(\d+(?:\.\d+)*)\s*[.)-]?\s+([A-Z][^\n]{2,140})$", line)
        if numbered_match:
            return f"{numbered_match.group(1)} {numbered_match.group(2).strip()}"

        section_match = re.match(r"^(Section\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$", line, flags=re.IGNORECASE)
        if section_match:
            return section_match.group(1).strip()

        article_match = re.match(r"^(Article\s+[A-Za-z0-9.\-]+\s*[:.-]?\s*[^\n]{2,160})$", line, flags=re.IGNORECASE)
        if article_match:
            return article_match.group(1).strip()

    return None


def _split_sentences(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", sentence).strip()
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text)
        if sentence.strip()
    ]


def _find_first_matching_sentence(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for sentence in _split_sentences(text):
        if regex.search(sentence):
            return sentence
    return ""


def _trim_sentence(text: str, max_chars: int = 220) -> str:
    if len(text) <= max_chars:
        return text
    window = text[:max_chars].rstrip()
    cut = window.rfind(" ")
    if cut >= 80:
        return window[:cut].rstrip() + "..."
    return window + "..."


def _strategic_takeaways(signals: dict[str, bool], markdown_chunk: str) -> list[str]:
    takeaways: list[str] = []

    category_patterns: list[tuple[str, str, bool]] = [
        ("Eligibility", r"\b(set-aside|small business|8\(a\)|hubzone|wosb|sdvosb|naics|size standard)\b", signals["set_aside_signal"] or signals["naics_signal"]),
        ("Evaluation", r"\b(evaluation|factor|section\s+m|tradeoff|lpta|best value)\b", signals["evaluation_signal"]),
        ("Past Performance", r"\b(past performance|cpars|references|recency|relevancy)\b", signals["past_performance_signal"]),
        ("Staffing and Transition", r"\b(key personnel|resume|staffing|labor category|fte|hours|transition|mobilization|phase-in)\b", signals["staffing_signal"] or signals["transition_signal"]),
        ("Pricing", r"\b(price|cost|ige|ceiling|nte|cost realism|wage determination)\b", signals["pricing_signal"]),
        ("Incumbent", r"\bincumbent\b", signals["incumbent_signal"]),
    ]

    for label, pattern, enabled in category_patterns:
        if not enabled:
            continue
        sentence = _find_first_matching_sentence(markdown_chunk, pattern)
        if not sentence:
            continue
        takeaways.append(f"{label} signal from this section: {_trim_sentence(sentence)}")
        if len(takeaways) >= 4:
            break

    return takeaways


def _strategic_next_steps(signals: dict[str, bool], markdown_chunk: str, has_assets: bool) -> list[str]:
    actions: list[str] = []

    if signals["set_aside_signal"] or signals["naics_signal"]:
        sentence = _find_first_matching_sentence(markdown_chunk, r"\b(set-aside|small business|8\(a\)|hubzone|wosb|sdvosb|naics|size standard)\b")
        if sentence:
            actions.append(f"Verify eligibility assumptions against this requirement language: {_trim_sentence(sentence, max_chars=180)}")

    if signals["evaluation_signal"]:
        sentence = _find_first_matching_sentence(markdown_chunk, r"\b(evaluation|factor|section\s+m|tradeoff|lpta|best value)\b")
        if sentence:
            actions.append(f"Align proposal volume emphasis to the stated evaluation language in this section: {_trim_sentence(sentence, max_chars=180)}")

    if signals["pricing_signal"]:
        sentence = _find_first_matching_sentence(markdown_chunk, r"\b(price|cost|ige|ceiling|nte|cost realism|wage determination)\b")
        if sentence:
            actions.append(f"Stress-test pricing assumptions using this section's pricing signal: {_trim_sentence(sentence, max_chars=180)}")

    if signals["staffing_signal"] or signals["transition_signal"]:
        sentence = _find_first_matching_sentence(markdown_chunk, r"\b(key personnel|resume|staffing|labor category|fte|hours|transition|mobilization|phase-in)\b")
        if sentence:
            actions.append(f"Validate staffing and mobilization feasibility against this requirement: {_trim_sentence(sentence, max_chars=180)}")

    if has_assets and actions:
        actions.append("Map these section findings to available reference assets to prepare opportunity-specific proposal proof points.")

    return actions[:4]


class ExtractorAgent(BaseAgent):
    name = "extractor"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        lines = [ln.strip() for ln in markdown_chunk.splitlines() if ln.strip()]
        key_lines = lines[:5]
        content = "\n".join(key_lines) if key_lines else "No content"
        heading = _detect_section_heading(markdown_chunk)

        if heading:
            content += f"\n\nDetected section heading: {heading}"

        if assets_context.strip() and key_lines:
            overlap = sorted(_tokenize(" ".join(key_lines)) & _tokenize(assets_context))
            if overlap:
                content += "\n\nReference overlap terms: " + ", ".join(overlap[:12])
            else:
                content += "\n\nReference overlap terms: none detected"

        return AgentResult(self.name, content)


class ReviewerAgent(BaseAgent):
    name = "reviewer"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        checks = []
        if "TODO" in markdown_chunk:
            checks.append("Found TODO markers needing resolution.")
        if len(markdown_chunk) < 200:
            checks.append("Chunk is short; context may be incomplete.")
        if assets_context.strip():
            overlap_count = len(_tokenize(markdown_chunk) & _tokenize(assets_context))
            checks.append(f"Reference alignment terms detected: {overlap_count}.")
        if not checks:
            checks.append("No obvious structural issues detected.")
        return AgentResult(self.name, " ".join(checks))


class AnalystAgent(BaseAgent):
    name = "analyst"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        words = [w for w in markdown_chunk.replace("\n", " ").split(" ") if w]
        unique = len(set(w.lower() for w in words))
        if assets_context.strip():
            shared = len(_tokenize(markdown_chunk) & _tokenize(assets_context))
            ref_terms = len(_tokenize(assets_context))
            return AgentResult(
                self.name,
                f"Word count: {len(words)}; unique terms: {unique}; shared-with-assets: {shared}/{ref_terms}.",
            )
        return AgentResult(
            self.name,
            f"Word count: {len(words)}; unique terms: {unique}.",
        )


class LegalRiskAgent(BaseAgent):
    name = "legal-risk"

    _keyword_pattern = re.compile(
        r"\b(naics|set-aside|small\s+business|8\(a\)|hubzone|wosb|sdvosb|"
        r"evaluation|section\s+m|factor|tradeoff|lpta|best\s+value|past\s+performance|cpars|"
        r"key\s+personnel|labor\s+category|fte|transition|mobilization|incumbent|"
        r"price|cost\s+realism|ceiling|nte|contract\s+vehicle|idiq|bpa|schedule)\b",
        re.IGNORECASE,
    )

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?;])\s+|\n+", markdown_chunk)
            if s.strip()
        ]
        matches: list[str] = []
        seen: set[str] = set()

        for sentence in sentences:
            if not self._keyword_pattern.search(sentence):
                continue
            compact = re.sub(r"\s+", " ", sentence)
            key = compact.lower()
            if key in seen:
                continue
            seen.add(key)
            matches.append(f"- {compact}")
            if len(matches) >= 8:
                break

        if not matches:
            return AgentResult(self.name, "No explicit BD gate signals were detected in this chunk.")

        return AgentResult(
            self.name,
            "Potential BD issues:\n" + "\n".join(matches),
        )


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"

    def run(self, markdown_chunk: str, assets_context: str = "") -> AgentResult:
        preview = _summary_preview(markdown_chunk)
        signals = _find_clause_signals(markdown_chunk)
        has_assets = bool(assets_context.strip())
        takeaways = _strategic_takeaways(signals, markdown_chunk)
        next_steps = _strategic_next_steps(signals, markdown_chunk, has_assets)
        heading = _detect_section_heading(markdown_chunk)

        if not takeaways:
            takeaways = ["No significant solicitation-specific BD issues were identified in this section."]

        output_lines = ["Summary preview: " + preview]
        if heading:
            output_lines.extend(["", "Section heading candidate: " + heading])
        output_lines.extend(["", "Strategic takeaways:"])
        output_lines.extend(f"- {item}" for item in takeaways)
        output_lines.append("")
        output_lines.append("Recommended next actions:")
        output_lines.extend(f"- {item}" for item in next_steps)

        if not has_assets:
            output_lines.append("")
            output_lines.append("Reference anchors: none detected")
            return AgentResult(self.name, "\n".join(output_lines))

        ref_terms = sorted(_tokenize(markdown_chunk) & _tokenize(assets_context))
        output_lines.append("")
        if ref_terms:
            output_lines.append("Reference anchors: " + ", ".join(ref_terms[:10]))
        else:
            output_lines.append("Reference anchors: none detected")
        return AgentResult(self.name, "\n".join(output_lines))
