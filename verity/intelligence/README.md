# VERITY Live Intelligence Pipeline

This folder is the heart of VERITY's automated knowledge pipeline.

## How it works

```
Nexla Feed (every 15 min)
        ↓
nexla_senso_update.py
  → Fetches breaking geopolitical news
  → Saves each article as .md in intelligence/live/
  → Git commits the new files
        ↓
GitHub Actions: intelligence-review.yml
  → Detects new files in intelligence/live/
  → Augment Code (auggie CLI) reviews each article:
      • Source credibility assessment
      • Propaganda signal detection
      • Intelligence priority rating (HIGH / MEDIUM / LOW)
      • Cross-article narrative analysis
  → Saves review to intelligence/reviews/
  → Commits the review back to the repo
        ↓
Senso Knowledge Base
  → All intelligence/live/ + intelligence/reviews/ uploaded
  → Verity agents query Senso for fresh, auggie-vetted intelligence
        ↓
VERITY Analysis
  → 7 parallel agents + Conflict Synthesizer
  → All grounded in continuously refreshed, AI-reviewed knowledge
```

## Folder structure

```
intelligence/
├── live/           # Raw articles from Nexla / Tavily (auto-generated)
│   └── YYYY-MM-DD_article-slug.md
├── reviews/        # Augment Code (auggie) intelligence assessments
│   └── YYYY-MM-DD_HH-MM-SS_review.md
└── README.md       # This file
```

## Running locally

```bash
# Full run: fetch → save → commit → upload to Senso
python scripts/nexla_senso_update.py

# Dry run: fetch and save only (no git commit, no Senso upload)
python scripts/nexla_senso_update.py --dry-run

# Manual auggie review of latest intelligence
auggie --print "Review the latest files in intelligence/live/ using the rules in .augment/rules/intelligence-review.md"
```

## GitHub Secrets required

| Secret | Description |
|--------|-------------|
| `NEXLA_API_URL` | Nexla data feed endpoint |
| `NEXLA_API_KEY` | Nexla authentication key |
| `TAVILY_API_KEY` | Tavily fallback search key |
| `SENSO_API_KEY` | Senso knowledge base key |
| `AUGMENT_SESSION_AUTH` | Augment Code session token (from `auggie login`) |
