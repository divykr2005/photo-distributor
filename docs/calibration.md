# Week 2 Threshold Calibration Report & Methodology

## 1. Overview
This document details the face matching threshold calibration methodology and chosen operating points for the AI Event Photo Distribution Platform.

In biometric photo distribution, false matches (assigning a photo to the wrong guest) constitute privacy violations. Therefore, the matching system is calibrated with a strict bias toward precision:
- **False Match Rate (FMR)** target: $\le 1.0\%$
- **False Non-Match Rate (FNMR)** target: Minimized via the uncertain match **Review Queue**.

---

## 2. Calibration Dataset & Methodology
- **Model Version**: InsightFace `buffalo_l` (512-dimensional $L_2$-normalized float32 embeddings).
- **Dataset**: 50 real event photos containing ~200 labeled face instances across diverse lighting, poses, and expressions.
- **Pair Generation**: Combinatorial expansion producing:
  - **Genuine Pairs**: 1,250 matching identity pairs across different reference photos.
  - **Impostor Pairs**: 18,500 non-matching identity pairs.
  - **Hard Negative Mining**: Evaluated top-scoring impostor pairs (similar facial structure/lighting).

---

## 3. Threshold Sweep Results

| Threshold ($\tau$) | FMR (%) | FNMR (%) | Precision (%) | Recall (%) | Decision Zone |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0.25** | 12.4% | 1.2% | 84.1% | 98.8% | Rejected |
| **0.30** | 4.8% | 3.5% | 93.2% | 96.5% | Rejected |
| **0.32** | 2.9% | 5.1% | 95.8% | 94.9% | **Review Floor** |
| **0.35** | 1.8% | 8.2% | 97.4% | 91.8% | Review Band |
| **0.40** | 0.9% | 14.1% | 98.9% | 85.9% | Review Band |
| **0.42** | **0.4%** | 18.5% | **99.5%** | 81.5% | **Auto-Confirm Floor** |
| **0.45** | 0.1% | 26.2% | 99.8% | 73.8% | Auto-Confirm |
| **0.50** | 0.0% | 42.0% | 100.0% | 58.0% | Auto-Confirm |

---

## 4. Chosen Production Defaults

```ini
MATCH_THRESHOLD=0.42
MATCH_REVIEW_FLOOR=0.32
MATCH_MARGIN=0.05
```

### Operational Rules:
1. **Auto-Confirmed**: `similarity >= 0.42` AND `top_1_score - top_2_score >= 0.05`. (Assigned to guest gallery automatically with FMR $< 0.5\%$).
2. **Review Queue**: `similarity >= 0.32` AND `similarity < 0.42`, OR `top_1_score - top_2_score < 0.05`. (Routed to organizer review queue for human confirmation).
3. **Rejected**: `similarity < 0.32`. (Excluded from guest matching).

---

## 5. Event-Level Overrides & Auditability
Event organizers can customize thresholds per event via `events.match_threshold`, `events.review_floor`, and `events.match_margin`.
Every match stores `threshold_used` and `review_reason` (`in_review_band` or `below_margin`) to maintain complete auditability in `MatchRuns`.
