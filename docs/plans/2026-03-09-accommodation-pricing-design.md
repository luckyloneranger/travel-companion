# Budget-Aware Accommodation Pricing — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ground accommodation pricing with budget context and Google price_level validation so hotel prices reflect the user's budget tier and destination reality.

## Problem

Accommodation pricing is 100% ungrounded LLM guessing:
- Scout LLM never receives the `budget` tier — prompt has no `{budget}` placeholder
- Enricher receives `budget_tier` parameter but never uses it
- Google's `price_level` (0-4) is stored but never used to validate/adjust prices
- Fallback placeholder is hardcoded $100/night regardless of budget or destination
- A "budget" trip to Bangkok could show $220/night; a "luxury" trip to Tokyo could show $170/night

## Design

### 1. Pass Budget to Scout Prompt

Add `{budget}` to `scout_user.md` so the LLM knows the price tier when estimating hotels.

### 2. Budget-to-Price-Level Mapping

| Budget Tier | Target `price_level` | Fallback USD Range |
|-------------|---------------------|-------------------|
| `budget` | 1-2 | $30-80 |
| `moderate` | 2-3 | $80-200 |
| `expensive` | 3-4 | $150-350 |
| `luxury` | 4 | $250+ (cap 600) |

### 3. Budget-Filtered Lodging Search

Enricher will:
1. Search for LLM's named hotel (current behavior)
2. If found, check `price_level` against budget tier
3. If mismatched, search for alternatives near same location filtered by budget price_levels
4. Pick best alternative (highest rated within budget)

### 4. Price Estimate Adjustment

If Google `price_level` exists, clamp `estimated_nightly_usd` to the tier's USD range:
- price_level=1 but LLM says $200 → clamp to $80
- price_level=4 but LLM says $80 → raise to $250
- No price_level → keep LLM estimate

### 5. Budget-Aware Fallback

Replace hardcoded $100 fallback with midpoint of budget tier's range.
