# Project Roadmap — Renewables Reconciliation API

_Last updated: 25 Nov 2025_

## Overview
The roadmap outlines the next development phases for the Renewable Reconciliation API prototype.  
The project is currently in **Phase I** (v0.1.13)

---

## Early Setup (by 6 Nov, achieved 2 Nov)
**Goal:** Establish clean environment, repo structure, and working FastAPI skeleton.  
**Deliverables:**
- [x] `.gitignore`, `README`, and `requirements.txt`
- [x] `app/main.py` with `/` and `/healthy` endpoints
- [x] Local run verified with screenshots
- [x] Roadmap and PowerShell helper scripts

---

## Phase I (by 18 Dec)
**Goal:** Minimal, working reconciliation endpoint that OpenRefine can call and get valid JSON back.
- [x] Define minimally viable reconciliation spec in code (request/response shapes).
- [x] Implement /reconcile endpoint (accept both GET query= and POST queries= forms).
- [ ] Build a lightweight, baseline reconcilitation algorithm:
    - [ ] Normalise project names
    - [ ] Compare names with substring or simple RapidFuzz ratio
    - [ ] Filter by approximate capactiy band (10%)
    - [ ] Return top-N candidates with crude confidence socre (e.g., ratiox100).
- [ ] Add required HTTP headers & encoding: Content-Type: application/json; charset=utf-8, CORS (for local dev), Cache-Control: no-store.
- [ ] Basic functionality tests (pytest TestClient) for status code, schema, and encoding.
- [ ] Example curl + README snippet so OpenRefine setup is trivial.
- [ ] Version bump and CHANGELOG.

---

## Phase II (by 9 Feb)
**Goal:** Make the implementation robust, well-documented, and testable to a 2:1 standard.
- [ ] Improve matching quality:
    - [ ] Swap crude ratio for proper RapidFuzz token-set or partial ratio.
    - [ ] Add feature weights and adjustable threshold.
- [ ] Introduce Pydantic models for request/response validation.
- [ ] Proper error handling & status codes (400 on bad input, 415 on wrong content-type).
- [ ] Logging config (structured INFO/ERROR) and config via env vars.
- [ ] Unit + integration tests; target ≥80% coverage.
- [ ] CI (GitHub Actions) to run tests/lint on push.
- [ ] Documentation: endpoint contract, examples, limitations, how to point OpenRefine to the service.
- [ ] Version bump and CHANGELOG.

---

## Phase III (by 10 Mar)
**Goal:** Extend the prototype with robustness, safety, and evaluative depth, achieving at least **two** of the below extensions.

### 1) Fuzzy matching [ ]
- **Tasks:** Add RapidFuzz (token_set_ratio / partial_ratio), normalise names, capacity tolerance, tech/type compatibility gates.
- **Acceptance:** ≥X% lift in recall at fixed precision on sample set; ablation note showing where fuzzy helps/hurts.

### 2) Confidence scoring [ ]
- **Tasks:** Combine features (name score, capacity delta, technology match, substation/TO cue) into a weighted score; expose `score` and `match` (boolean via threshold).
- **Acceptance:** Threshold rationale documented; precision/recall curve plotted; default threshold chosen and justified.

### 3) Performance evaluation [ ]
- **Tasks:** Time endpoints on N queries; record p50/p95 latency and throughput on the sample dataset; add simple benchmark script.
- **Acceptance:** Report p50/p95 and memory footprint; note any hotspots and one optimisation taken (e.g., precomputed indices).

### 4) API access controls [ ]
- **Tasks:** Add simple API key via header; rate-limit per IP/key; CORS tightened for local tools only.
- **Acceptance:** Requests without key → 401; over limit → 429; README documents how to set/use the key.

### 5) Abuse resistance [ ]
- **Tasks:** Input size caps, request body schema limits, timeout/guardrails, basic logging of anomalous patterns.
- **Acceptance:** Oversized payload returns 413; excessive batch size returns 400 with hint; timeouts handled gracefully.

### 6) Data provenance monitoring [ ]
- **Tasks:** Attach provenance fields to responses (`source`, `dataset_version`, `retrieved_at`); log mapping rules applied; keep a small `provenance.jsonl`.
- **Acceptance:** Each result includes provenance; an auditor can trace a candidate back to source rows and mapping steps.

**Deliverables:** short evaluation report (metrics + plots), updated README (usage, keys, limits), config sample (`.env.example`), and version bump.
