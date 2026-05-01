from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdf_multi_agent_analysis.pipeline import (
    _build_scorecard,
    _derive_company_capacity_signals,
    _extract_company_profile_section,
    _score_issue_line,
)


def _make_scorecard(analysis_report: str, issues: list[str]) -> str:
    issues_report = "# BD Issues Summary: demo\n\nPotential BD issues:\n" + "\n".join(f"- {item}" for item in issues)
    scorecard, _recommendation, _unused, _rows = _build_scorecard(analysis_report, issues_report)
    return scorecard


def _make_scorecard_with_capacity(analysis_report: str, issues: list[str], team_size: str, key_personnel: str) -> str:
    issues_report = "# BD Issues Summary: demo\n\nPotential BD issues:\n" + "\n".join(f"- {item}" for item in issues)
    scorecard, _recommendation, _unused, _rows = _build_scorecard(
        analysis_report,
        issues_report,
        company_capacity_signals={
            "team_size": team_size,
            "key_personnel": key_personnel,
            "personnel_count": 2,
        },
    )
    return scorecard


def test_recommendation_selective_pursue_when_evidence_is_rich() -> None:
    analysis_report = "\n".join(
        [
            "PWS technical approach deliverable methodology statement of work scope quality control.",
            "Past performance CPARS recency relevancy reference history with multiple references.",
            "Small business set-aside HUBZone SDVOSB WOSB certification and SAM registration.",
            "Contract vehicle IDIQ BPA Schedule GWAC NAICS ordering period with active access.",
            "Key personnel resume labor category FTE hours transition mobilization clearance staffing plan.",
            "Technical approach includes quality control methodology and scoped deliverables.",
        ]
    )
    scorecard = _make_scorecard(analysis_report, ["Mandatory eligibility gate with Section M evaluation factor."])

    assert "Overall BD fit score:" in scorecard
    assert "Selective Pursue" in scorecard


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


def test_team_capacity_is_capped_for_two_person_key_team() -> None:
    analysis_report = "Key personnel resume labor category FTE hours transition mobilization clearance staffing."
    issues = ["Transition and key personnel requirements create schedule risk."]

    scorecard = _make_scorecard_with_capacity(
        analysis_report,
        issues,
        team_size="1-5",
        key_personnel="1 PM and 1 AI lead",
    )

    team_capacity_row = next(
        line for line in scorecard.splitlines() if line.startswith("| Team Capacity |")
    )
    assert "35/100" in team_capacity_row
    assert "Adjusted using intake profile" in scorecard


def test_team_capacity_penalized_for_missing_critical_roles() -> None:
    analysis_report = "Key personnel resume labor category FTE hours transition mobilization clearance staffing."
    issues = ["Transition and key personnel requirements create schedule risk."]

    scorecard = _make_scorecard_with_capacity(
        analysis_report,
        issues,
        team_size="11-50",
        key_personnel="AI lead",
    )

    team_capacity_row = next(
        line for line in scorecard.splitlines() if line.startswith("| Team Capacity |")
    )
    assert "45/100" in team_capacity_row
    assert "missing capture leadership" in scorecard


def test_extract_company_profile_section_keeps_nested_headings() -> None:
    markdown = "\n".join(
        [
            "# Source",
            "Some solicitation text.",
            "## Submitted Company Profile",
            "**Procurement Type:** International Development",
            "## Past Performance Summary",
            "Experience with USAID programming.",
            "## Capability Statement — capability.docx",
            "GEDSI delivery and donor-aligned implementation.",
            "## Supporting Document — testimonials.docx",
            "Chemonics and USAID testimonials.",
        ]
    )

    profile = _extract_company_profile_section(markdown)

    assert "## Past Performance Summary" in profile
    assert "## Capability Statement — capability.docx" in profile
    assert "## Supporting Document — testimonials.docx" in profile


def test_intl_scorecard_uses_profile_text_for_signal_count() -> None:
    analysis_report = "Generic summary text with no intl scoring keywords."
    issues_report = "# BD Issues Summary: demo\n\nPotential BD issues:\n- Generic issue line for formatting only."
    company_profile_text = "\n".join(
        [
            "**Procurement Type:** International Development",
            "## Past Performance Summary",
            "USAID delivery experience across Bangladesh, Zambia, and Egypt.",
            "## Capability Statement — capability.docx",
            "Strong GEDSI and inclusion integration with donor-aligned implementation.",
            "## Supporting Document — testimonials.docx",
            "Client testimonials from USAID and Chemonics confirm donor alignment.",
            "## Key Personnel",
            "GEDSI specialist and donor compliance advisor.",
        ]
    )

    scorecard, _recommendation, _unused, _rows = _build_scorecard(
        analysis_report,
        issues_report,
        procurement_type="intl-dev",
        company_profile_text=company_profile_text,
    )

    donor_row = next(line for line in scorecard.splitlines() if line.startswith("| Donor and Funder Alignment |"))
    gedsi_row = next(line for line in scorecard.splitlines() if line.startswith("| GEDSI and Inclusion Fit |"))

    assert "Signals found: 0 positive" not in donor_row
    assert "Signals found: 0 positive" not in gedsi_row


def test_capacity_signals_fallback_to_companion_source_markdown(tmp_path) -> None:
    source_md = tmp_path / "sample.md"
    final_md = tmp_path / "sample-final.md"

    source_md.write_text(
        "\n".join(
            [
                "# Converted Markdown",
                "## Submitted Company Profile",
                "**Procurement Type:** International Development",
                "## Team Size",
                "11-50",
                "## Key Personnel",
                "Capture Manager, GEDSI Specialist",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    final_md.write_text("# Final Synthesized Output\n", encoding="utf-8")

    signals = _derive_company_capacity_signals(final_md.read_text(encoding="utf-8"), final_md.as_posix())

    assert signals["team_size"] == "11-50"
    assert "GEDSI Specialist" in str(signals["key_personnel"])
