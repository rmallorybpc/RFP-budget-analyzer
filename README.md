# MarketEdge RFP Budget Analyzer

> AI-powered federal RFP analysis for business development teams. Submit a solicitation, receive a structured capture intelligence brief with company fit score, PWS labor category mapping, and a GSA-based budget estimate.

---

## Overview

Federal contractors spend days manually analyzing RFPs before deciding whether to pursue an opportunity. The MarketEdge RFP Budget Analyzer compresses that work into hours. A BD team submits a solicitation PDF through a simple intake form, and a multi-agent AI pipeline produces a structured Capture Intelligence Brief covering requirements extraction, evaluation criteria, competitive landscape, win themes, and a company-specific fit score with a GSA-based budget estimate.

The tool is designed for capture managers, BD leads, and proposal coordinators at federal contractors who need to quickly assess whether an opportunity is worth pursuing and what it would cost to compete.

**Live intake form:** https://marketedgeglobal.github.io/RFP-budget-analyzer/

---

## What It Produces

Each submission generates a **BD Opportunity Assessment** covering:

- Opportunity summary — agency, contract type, NAICS, set-aside, period of performance, estimated value
- Requirements extraction — mandatory qualifications, deliverables, staffing, special requirements
- Evaluation criteria and weightings — factors, pass/fail gates, oral presentation requirements
- PWS labor categories — identified roles, estimated level of effort, wage determination applicability
- Compliance obligations — FAR/DFARS clauses, certifications, submission format requirements
- Competitive landscape — incumbent indicators, sole source flags, bundling analysis
- Incumbent analysis — recompete vs. new requirement, advantage/disadvantage assessment
- BD risk factors — unrealistic timelines, restrictive qualifications, vague evaluation criteria
- Price to win indicators — LPTA vs. best value, IGE disclosure, cost realism requirements
- Teaming recommendations — capability gaps, subcontracting goals, teaming structure guidance
- Small business considerations — set-aside eligibility, size standard analysis, SB participation goals
- Proposal response strategy — bid/no-bid indicators, volume risk, recommended emphasis
- Transition and mobilization risk — funded transition, clearance timelines, GFE dependencies
- Win theme candidates — three to five themes tied to evaluation criteria and agency pain points
- Questions for the Q&A period — five to ten clarifying questions for the solicitation Q&A window
- Glossary of acronyms and terms — all non-standard acronyms defined

Followed by a **Stage E Capture Intelligence Brief** that adds:

- Weighted company fit score across five dimensions
- PWS labor category to GSA rate mapping table
- Multi-year budget estimate by labor category
- Custom past performance statements aligned to evaluation criteria
- Pursue / No Pursue recommendation with strategic rationale

---

## How It Works

```
Company submits intake form
  → Cloudflare Worker stores PDF in R2, logs to KV,
    fires GitHub repository dispatch
  → rfp-intake-dispatch workflow downloads PDF from R2,
    writes company-profile.md, commits both to repo
  → convert-rfp-pdf-to-markdown converts PDF to markdown,
    appends company profile as final section
  → local-multistage-refinement runs four-stage AI
    refinement pipeline producing final BD assessment
  → MarketEdge reviews output, runs Stage E manually,
    delivers Capture Intelligence Brief to company
```

---

## Repository Structure

```
marketedgeglobal/RFP-budget-analyzer/
│
├── .github/
│   └── workflows/
│       ├── rfp-intake-dispatch.yml        # Triggered by Cloudflare Worker dispatch.
│       │                                  # Downloads PDF from R2, writes company
│       │                                  # profile, commits to repo.
│       ├── convert-rfp-pdf-to-markdown.yml # Converts PDF to markdown, appends
│       │                                  # company profile under
│       │                                  # ## Submitted Company Profile
│       └── local-multistage-refinement.yml # Four-stage multi-agent AI refinement.
│                                          # Produces final BD Opportunity Assessment.
│
├── docs/
│   └── intake-form/
│       └── index.html                     # Public intake form. Hosted on GitHub Pages.
│                                          # Submits to Cloudflare Worker endpoint.
│
├── prompts/
│   ├── 01-stage-a.md                      # Stage A: Initial requirements extraction
│   ├── 02-stage-b.md                      # Stage B: Evaluation criteria analysis
│   ├── 03-stage-c.md                      # Stage C: Competitive and risk assessment
│   ├── 04-stage-d.md                      # Stage D: Final BD assessment synthesis
│   └── 05-fit-score-budget.md             # Stage E: Company fit score, labor category
│                                          # mapping, GSA budget estimate. Run manually.
│
├── rfp-pdfs/
│   └── [submissionId]/                    # One subfolder per submission.
│       ├── [rfp-filename].pdf             # Original PDF committed by dispatch workflow.
│       └── company-profile.md            # Company capabilities extracted from form.
│
├── rfp-markdown/
│   └── generated/
│       └── [submissionId]/               # One subfolder per submission.
│           └── [rfp-filename].md         # Final refined BD Opportunity Assessment.
│
├── assets/
│   └── gsa-rate-reference.md             # GSA schedule rate reference table used
│                                         # by Stage E budget estimation prompt.
│
└── README.md
```

---

## Architecture

```
┌─────────────────────────────────┐
│  Intake Form (GitHub Pages)     │
│  marketedgeglobal.github.io/    │
│  RFP-budget-analyzer/           │
└────────────────┬────────────────┘
                 │ multipart/form-data POST
                 ▼
┌─────────────────────────────────┐
│  Cloudflare Worker              │
│  tmg-rfp-intake                 │
│  ross-mallory.workers.dev       │
│                                 │
│  • Validates and stores PDF     │
│    in Cloudflare R2             │
│  • Logs submission to KV        │
│  • Fires GitHub repository      │
│    dispatch event               │
└────────────────┬────────────────┘
                 │ repository_dispatch: rfp-submission
                 ▼
┌─────────────────────────────────┐
│  GitHub Actions Pipeline        │
│  marketedgeglobal/              │
│  RFP-budget-analyzer            │
│                                 │
│  Stage 1: rfp-intake-dispatch   │
│  • Downloads PDF from R2        │
│  • Writes company-profile.md   │
│  • Commits to rfp-pdfs/        │
│                                 │
│  Stage 2: convert-pdf-to-md     │
│  • Converts PDF to markdown     │
│  • Appends company profile      │
│  • Commits to rfp-markdown/    │
│                                 │
│  Stage 3: multistage-refinement │
│  • Stage A: Requirements        │
│  • Stage B: Evaluation criteria │
│  • Stage C: Competitive/risk    │
│  • Stage D: BD synthesis        │
│  • Commits final assessment     │
└────────────────┬────────────────┘
                 │ Manual review
                 ▼
┌─────────────────────────────────┐
│  Stage E (Manual)               │
│  prompts/05-fit-score-budget.md │
│                                 │
│  • Company fit score            │
│  • GSA budget estimate          │
│  • Capture Intelligence Brief   │
│  • Delivered to company         │
└─────────────────────────────────┘
```

---

## Infrastructure

| Component | Service | Purpose |
|---|---|---|
| Intake form | GitHub Pages | Public-facing submission form |
| API endpoint | Cloudflare Workers | Form processing, R2 storage, dispatch trigger |
| PDF storage | Cloudflare R2 | Stores submitted RFP PDFs privately |
| Submission log | Cloudflare KV | Tracks all submissions and pipeline status |
| Admin dashboard | Cloudflare Worker `/admin` | Submission queue with status and dispatch diagnostics |
| Pipeline | GitHub Actions | PDF conversion and multi-stage AI refinement |
| AI model | GitHub Models (GPT-4o) | Powers all four refinement stages |
| Stage E | Claude (manual) | Company fit score and budget estimate |

---

## Intake Form Fields

The intake form collects both the RFP document and company capability information. All fields are passed through the pipeline and appended to the converted markdown so the AI analysis can cross-reference company fit against RFP requirements.

| Field | Description |
|---|---|
| Company Name | Submitting company |
| Contact Name | Primary contact for delivery |
| Contact Email | Analysis delivered here |
| NAICS Codes | Primary and secondary codes |
| Certifications | 8(a), HUBZone, SDVOSB, WOSB, EDWOSB, VOSB, ISO 9001, CMMI |
| Contract Vehicles | GSA schedules, GWACs, agency IDIQs |
| Past Performance Summary | Up to 200 words of relevant past performance |
| Team Size | Employee range selection |
| Key Personnel Summary | Key staff qualifications and experience |
| RFP PDF | Federal solicitation PDF, max 25MB |

---

## Admin Dashboard

A private submission tracking dashboard is available at:

```
https://tmg-rfp-intake.ross-mallory.workers.dev/admin?key=YOUR_ADMIN_KEY
```

Shows all submissions with company, contact, RFP filename, pipeline status, dispatch diagnostics, and submission ID. Status values progress from `Received` → `Pipeline Triggered` → `Ready for Review` → `Delivered`.

---

## Setup

Full deployment instructions are in [SETUP.md](./SETUP.md).

Required accounts and services:
- GitHub account with org access to `marketedgeglobal`
- Cloudflare account (free tier sufficient)
- GitHub Models enabled on the repository
- GitHub fine-grained PAT with Actions and Contents read/write on this repo

---

## Roadmap

**v2 Enhancements (planned)**
- Automated email delivery of Capture Intelligence Brief via Resend
- Stage E automated as pipeline Stage 5
- Competitor analysis via SAM.gov and USASpending.gov integration
- Ideal team structure and suggested team profiles
- Win probability assessment with structured confidence scoring
- Longitudinal submission tracking and trend analysis

**Future Use Case**
- Contractor vs. FTE staffing analysis for non-federal companies — assessing whether a contractor engagement is more cost-effective than a full-time hire for a specific capability gap

---

## About MarketEdge

MarketEdge provides AI enablement and program management consulting for federal contractors and international development organizations. The RFP Budget Analyzer is built on MarketEdge's federal contracting domain expertise and AI pipeline architecture.

**Website:** https://www.marketedgeglobal.com
