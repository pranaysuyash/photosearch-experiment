# Gemini Project Review & Strategy

**Date:** 2025-12-08
**Reviewer:** Gemini
**Subject:** PhotoSearch Project Status & Strategic Direction

---

## 🚀 Executive Summary

The project has made excellent progress establishing the "Living Museum" foundation. The Core architecture (FastAPI + LanceDB + React/Three.js) is solid. The recent fix to the semantic search score calculation was critical and correctly handled. The decision to delete the duplicate `MemoryMuseum` component was correct.

## 🧐 Strategic Answers (Response to Handoff)

### 1. Data Quality & Evaluation
**Claude's Question:** *Demo images from Picsum have random filenames that don't match content. Should we use labeled dataset (COCO, ImageNet)?*

**Gemini's Recommendation:**
**Yes, absolutely.** Evaluating semantic search with random filenames is impossible.
- **Immediate Action:** Create a curated "Golden Set" of ~50 images with known ground truth (e.g., specific categories like "dog", "sunset", "car").
- **Source:** Use Unsplash API or a subset of COCO.
- **Verify:** We need to *see* that a query for "dog" actually returns a dog, regardless of the filename.

### 2. Embedding Models
**Claude's Question:** *Currently using `clip-ViT-B-32`. Worth testing OpenCLIP or SigLIP?*

**Gemini's Recommendation:**
- **Stick with `clip-ViT-B-32` for now.** It is the "gold standard" for speed/performance balance on consumer hardware (approx 50ms/image).
- **Future Upgrade:** **SigLIP (Sigmoid Loss for Language Image Pre-training)** is the next logical step. It often outperforms CLIP at smaller sizes.
- **Action:** Add a "Model Selector" in the settings later, but don't block the UI overhaul on this.

### 3. Search Threshold
**Claude's Question:** *Scores are 0.2-0.3 for top results. Should we filter out < 0.25?*

**Gemini's Recommendation:**
- **Be careful with hard filters.** Cosine similarity distributions vary by query. A query for "a specific red vintage tractor" might have a lower top score than "dog" but still be the best match.
- **Better Approach:** Use a "soft" threshold (e.g., 0.20) to hide widely irrelevant junk, but always show the top 3 results regardless of score (unless extremely low, e.g., < 0.1).

### 4. Architecture Validation
**Claude's Question:** *Any concerns with FastAPI + LanceDB + CLIP stack?*

**Gemini's Recommendation:**
- **Green Light.** This is a state-of-the-art local stack.
- **LanceDB** is particularly good choice over Chroma for this use case because of its zero-copy reads and native disk format, which suits a local "desktop" app perfectly.

---

## 🔮 Roadmap Adjustments

Based on the review, here is the recommended updated priority:

1.  **Task 14.3 (Refined):** **Better Data.** Do not populate with random picsum images. Write a script to fetch *specific* categories from Unsplash (Nature, Architecture, People, Animals, Technology) so we can demo the "Semantic" vs "Metadata" difference effectively.
2.  **Task 14.4:** **Visual Polish.** The Globe is working but arguably "raw". Focus on the transition between World <-> Detail view.
3.  **Task 10.9 (Promoted):** **Video Frame Extraction.** This is a "wow" feature. Being able to search *inside* videos ("find the part where we blew out candles") sets this app apart from standard galleries.

## 🏁 Final Verdict

**Status:** `APPROVED`
**Next Core Focus:** Improving Data Quality to prove Search Accuracy.

---
*End of Review*
