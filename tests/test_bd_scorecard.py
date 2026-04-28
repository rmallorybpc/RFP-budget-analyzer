from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_multi_agent_analysis.pipeline import _build_scorecard, _score_issue_line


def _make_scorecard(analysis_report: str, issues: list[str]) -> str:
    issues_report = "# BD Issues Summary: demo\n\nPotential BD issues:\n" + "\n".join(f"- {item}" for item in issues)
    scorecard, _recommendation, _unused, _rows = _build_scorecard(analysis_report, issues_report)
    return scorecard


def test_recommendation_strong_pursue_when_evidence_is_rich() -> None:
    analysis_report = "\n".join(
        [
            "PWS technical approach deliverable statement of work scope.",
            "Past performance CPARS recency relevancy similar scope references.",
            "Set-aside small business HUBZone SDVOSB WOSB with SAM registration.",
            "Contract vehicle IDIQ BPA Schedule GWAC NAICS ordering period.",
            "Key personnel resume labor category FTE hours transition mobilization clearance staffing.",
        ]
    )
    scorecard = _make_scorecard(analysis_report, ["Mandatory eligibility gate with Section M evaluation factor."])

    assert "Overall BD fit score:" in scorecard
    assert "Strong Pursue" in scorecard


def test_recommendation_pass_when_no_bd_evidence_exists() -> None:
    analysis_report = "This text is intentionally generic and does not include scoring keywords."
    scorecard = _make_scorecard(analysis_report, ["No explicit issue text."])

    assert "Overall BD fit score:" in scorecard
    assert "Pass" in scorecard


def test_disqualifier_issue_scores_above_boilerplate_issue() -> None:
    disqualifier = "Offeror will not receive an award if required credentials are missing and quote is non-responsive."
    boilerplate = "Clause is incorporated by reference with same force and effect and computer generated forms."

    assert _score_issue_line(disqualifier) > _score_issue_line(boilerplate)


def test_top_issue_order_prioritizes_bid_impact() -> None:
    analysis_report = "PWS statement of work. Evaluation factor tradeoff best value."
    issues = [
        "Clause is incorporated by reference with same force and effect and computer generated forms.",
        "Offeror will not receive an award if required credentials are missing and quote is non-responsive.",
        "Transition and key personnel requirements create schedule risk.",
    ]
    scorecard = _make_scorecard(analysis_report, issues)

    lines = [line.strip() for line in scorecard.splitlines() if line.strip()]
    top_issue_line = next(line for line in lines if line.startswith("1. ["))

    assert "not receive an award" in top_issue_line.lower()
