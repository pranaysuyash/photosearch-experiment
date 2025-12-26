# AI Providers & Services Guide

**Created by:** Antigravity (AI Assistant)
**Date:** 2025-12-06
**Purpose:** Comprehensive guide to AI providers, models, and services for photo search

---

## Overview

This document provides detailed information about various AI providers that can be used for the photo search application, including their capabilities, pricing, and use cases.

---

## Image Embedding Providers

### OpenAI CLIP
**Best For:** High-quality image-text embeddings

**Models:**
- `clip-vit-base-patch32` - Balanced performance
- `clip-vit-large-patch14` - Higher quality, slower

**Pricing:**
- Embeddings API: ~$0.0001 per image

**Pros:**
- Excellent quality
- Well-documented API
- Reliable uptime

**Cons:**
- Requires API key
- Costs can add up with large datasets

**Implementation:**
```python
import openai
response = openai.Embedding.create(
    model="clip-vit-base-patch32",
    input=image_base64
)
```

---

### HuggingFace CLIP Models
**Best For:** Free, local inference

**Models:**
- `openai/clip-vit-base-patch32`
- `openai/clip-vit-large-patch14`
- `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` - Very high quality

**Pricing:**
- Free (local inference)
- Inference API: ~$0.00006 per image

**Pros:**
- Free for local use
- Many model variants
- Open source

**Cons:**
- Slower on CPU
- Requires GPU for good performance
- Model download required

**Implementation:**
```python
from transformers import CLIPProcessor, CLIPModel
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
```

---

### Replicate
**Best For:** Easy API access to various models

**Models:**
- CLIP variants
- Custom fine-tuned models

**Pricing:**
- Pay per second of compute
- ~$0.0001-0.001 per image

**Pros:**
- Easy to use
- Many model options
- No infrastructure needed

**Cons:**
- Can be expensive for large batches
- Cold start latency

**Implementation:**
```python
import replicate
output = replicate.run(
    "andreasjansson/clip-features:...",
    input={"image": image_url}
)
```

---

## Image Captioning & Description

### OpenAI GPT-4 Vision
**Best For:** High-quality image descriptions

**Models:**
- `gpt-4-vision-preview`
- `gpt-4-turbo` (with vision)

**Pricing:**
- ~$0.01 per image (varies by detail level)

**Pros:**
- Excellent quality
- Detailed descriptions
- Understands context

**Cons:**
- Expensive for large datasets
- Rate limits

---

### Replicate - BLIP/BLIP-2
**Best For:** Cost-effective captioning

**Models:**
- `salesforce/blip`
- `salesforce/blip-2`

**Pricing:**
- ~$0.0001-0.0005 per image

**Pros:**
- Good quality
- Fast inference
- Cost-effective

**Cons:**
- Less detailed than GPT-4V
- Generic captions

---

### HuggingFace - Local Captioning
**Best For:** Free, offline captioning

**Models:**
- `Salesforce/blip-image-captioning-base`
- `Salesforce/blip-image-captioning-large`
- `microsoft/git-base`

**Pricing:**
- Free (local)

**Pros:**
- Completely free
- Privacy (no data sent externally)
- Fast with GPU

**Cons:**
- Requires local setup
- Quality varies

---

## Object Detection

### Roboflow
**Best For:** Custom object detection models

**Features:**
- Pre-trained models
- Custom model training
- Easy API

**Pricing:**
- Free tier: 1,000 API calls/month
- Paid: Starting at $49/month

**Pros:**
- Easy to use
- Custom training
- Good documentation

**Cons:**
- Limited free tier
- Requires account setup

---

### HuggingFace - DETR/YOLO
**Best For:** Free object detection

**Models:**
- `facebook/detr-resnet-50`
- `hustvl/yolos-tiny`
- `ultralytics/yolov8`

**Pricing:**
- Free (local)

**Pros:**
- Free
- Good accuracy
- Multiple model options

**Cons:**
- Requires local setup
- Slower without GPU

---

## Fast Inference Providers

### Groq
**Best For:** Ultra-fast LLM inference

**Models:**
- `llama-3.1-70b`
- `mixtral-8x7b`

**Pricing:**
- ~$0.0001 per 1K tokens

**Pros:**
- Extremely fast
- Low cost
- Good quality

**Cons:**
- Limited to text (no vision yet)
- Newer service

**Use Case:**
- Text-based search refinement
- Tag generation from captions

---

### Cerebras
**Best For:** Fast, efficient inference

**Models:**
- `llama-3.1-8b`
- `llama-3.1-70b`

**Pricing:**
- Competitive with Groq

**Pros:**
- Very fast
- Cost-effective
- Reliable

**Cons:**
- Text-only currently

---

## Image Generation (Future Use)

### Fal.ai
**Best For:** Fast image generation

**Models:**
- Stable Diffusion variants
- FLUX models

**Pricing:**
- ~$0.001-0.01 per image

**Pros:**
- Very fast
- Multiple models
- Good quality

**Cons:**
- Costs can add up

---

### Replicate
**Best For:** Variety of generation models

**Models:**
- Stable Diffusion XL
- Midjourney-style models
- Custom models

**Pricing:**
- Pay per second

---

## Multi-Provider Aggregators

### OpenRouter
**Best For:** Single API for multiple providers

**Features:**
- Access to 100+ models
- Unified API
- Automatic fallbacks

**Pricing:**
- Varies by model
- Usually competitive

**Pros:**
- One API key for many models
- Easy provider switching
- Automatic fallbacks

**Cons:**
- Slight markup on some models
- Another abstraction layer

**Recommended For:**
- Production deployments
- Multi-model experimentation

---

## Recommended Provider Strategy

### Learning Phase (Tasks 1-5)
**Primary:** HuggingFace (local, free)
- CLIP for embeddings
- BLIP for captions

**Fallback:** OpenAI (paid, high quality)
- For comparison and quality benchmarking

---

### Development Phase (Tasks 6-10)
**Primary:** Mix of providers
- HuggingFace for embeddings (free)
- OpenAI for high-quality captions (paid)
- Replicate for specialized models (paid)

**Rationale:** Balance cost and quality

---

### Production Phase (Tasks 11-12)
**Primary:** OpenRouter
- Unified API
- Multiple model options
- Automatic fallbacks

**Backup:** Local models
- For privacy-sensitive data
- Cost optimization

---

## Cost Estimation

### Small Dataset (1,000 images)
- **HuggingFace (local):** $0
- **OpenAI CLIP:** ~$0.10
- **Replicate:** ~$0.10-1.00

### Medium Dataset (10,000 images)
- **HuggingFace (local):** $0
- **OpenAI CLIP:** ~$1.00
- **Replicate:** ~$1.00-10.00

### Large Dataset (100,000 images)
- **HuggingFace (local):** $0 (but requires GPU)
- **OpenAI CLIP:** ~$10.00
- **Replicate:** ~$10.00-100.00

**Recommendation:** Start with HuggingFace for learning, add paid providers as needed

---

## API Key Setup

### Required Environment Variables
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Replicate
REPLICATE_API_TOKEN=r8_...

# HuggingFace (optional, for private models)
HUGGINGFACE_API_KEY=hf_...

# Roboflow
ROBOFLOW_API_KEY=...

# Groq
GROQ_API_KEY=gsk_...

# Cerebras
CEREBRAS_API_KEY=...

# Fal.ai
FAL_KEY=...

# OpenRouter (multi-provider)
OPENROUTER_API_KEY=sk-or-...
```

---

## Model Selection Guide

### For Image Embeddings
**Best Quality:** OpenAI CLIP Large
**Best Free:** HuggingFace CLIP ViT-L/14
**Best Speed:** HuggingFace CLIP ViT-B/32 (local with GPU)

### For Image Captions
**Best Quality:** GPT-4 Vision
**Best Free:** HuggingFace BLIP-2
**Best Balance:** Replicate BLIP-2

### For Object Detection
**Best Quality:** Roboflow (custom trained)
**Best Free:** HuggingFace DETR
**Best Speed:** YOLOv8 (local)

---

## Rate Limits & Best Practices

### OpenAI
- **Tier 1:** 3,500 requests/min
- **Best Practice:** Batch requests, use caching

### Replicate
- **Limit:** Varies by model
- **Best Practice:** Use async requests

### HuggingFace Inference API
- **Free Tier:** Rate limited
- **Best Practice:** Use local models for heavy usage

### Groq
- **Limit:** High (varies by tier)
- **Best Practice:** Very fast, good for real-time

---

## Testing & Comparison

### Recommended Approach
1. **Start with HuggingFace** - Free, learn the concepts
2. **Add OpenAI** - Compare quality
3. **Test Replicate** - Evaluate specialized models
4. **Benchmark** - Compare speed, cost, quality

### Metrics to Track
- **Quality:** Embedding similarity scores, caption accuracy
- **Speed:** Inference time per image
- **Cost:** Total cost per 1,000 images
- **Reliability:** Uptime, error rates

---

**Document Status:** Living Document - Updated as new providers are tested
**Next Update:** After Task 3 (Embedding Generation) implementation
