# PRD: tt_agent — AI-Powered TikTok Content Intelligence Agent

> Track: Kaggle Agents for Business
> SDLC: AI-Augmented, PRD-driven, Agent-first architecture
> Target Platform: TikTok + TikTok Shop

---

## 1. Problem Statement

### The Business Problem
Small businesses and independent creators on TikTok face a structural disadvantage:

- **No competitive intelligence**: Can't systematically analyze why competitor videos go viral
- **No scripting framework**: Content is improvised without hook strategy or retention tactics
- **No platform adaptation**: Same content pushed to TikTok, Reels, and Shorts without optimization
- **No feedback loop**: Publish-and-pray with no way to learn from performance

**Result**: 95% of small business TikTok accounts fail to reach 1,000 followers within 6 months. The creator economy is gated by an invisible wall of content operations expertise.

### The Solution
tt_agent is a **multi-agent content intelligence system** that gives any small business the content capability of a venture-backed brand. It transforms "I found a viral video" into "I have a tested script with shot-by-shot filming instructions" in under 5 minutes.

### Real-World Validation
Pilot-tested with 芮玛鞋城 (Rui Ma Shoe City), a family-run shoe store in Beijing. Before tt_agent: 1-2 improvised posts/week, no content strategy. After: 5 structured posts/week, hook-tested scripts, 4-3-2-1 content mix.

---

## 2. User Personas

### Primary: Small Business Owner
- Runs a physical store or TikTok Shop
- Smartphone-only, no video production background
- Pain: "I know I should be on TikTok, but I don't know what to film"

### Secondary: Independent Creator
- Building a personal brand on TikTok
- Some content experience but no systematic process
- Pain: "I spend 4 hours analyzing one competitor video"

### Tertiary: Agency / Content Manager
- Managing multiple brand accounts
- Needs scalable, repeatable content operations
- Pain: "I can't clone myself across 10 client accounts"

---

## 3. Agent Architecture

```
                    ┌──────────────────┐
                    │   Orchestrator   │
                    │   (Task Router)  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼──────┐
   │Deconstruct│      │  Script      │      │  Filming   │
   │  Agent    │ ──── │  Agent       │ ──── │  Agent     │
   │(5L分析)   │      │(Adaptation)  │      │(Shot List) │
   └──────────┘      └─────────────┘      └────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
        │  Guardrail │ │ Platform │ │ Performance │
        │  Agent     │ │ Agent    │ │ Agent       │
        │(Compliance)│ │(Adapt)   │ │(Analytics)  │
        └────────────┘ └──────────┘ └─────────────┘
```

### Agent Roles

| Agent | Responsibility | Input | Output |
|-------|---------------|-------|--------|
| Orchestrator | Route tasks, manage context, human checkpoints | Transcript | Pipeline state |
| Deconstruct | 5-layer analysis (Hook/Structure/Emotion/Rhythm/Hypothesis) | Transcript | Structured analysis |
| Script | Adapt for target brand with constraints | Deconstruction | Script + Caption |
| Filming | Shot list, camera angles, lighting, props | Script | Filming checklist |
| Guardrail | Compliance check (TikTok policies, FTC, copyright) | Script | Issue list |
| Platform | Adapt for TikTok/Reels/Shorts | Script | Platform variants |
| Performance | Predict viral potential, suggest A/B hooks | Script + Deconstruction | Hook scores |

### Communication Protocol
Agents share a **Context Document** (JSON) that accumulates as each agent contributes:

```
Transcript → Deconstruct → Script → Filming → Guardrail → Platform → Output
```

---

## 4. TikTok-Specific Features

### Hook Library (viral patterns observed on TikTok)
- **Pattern Interrupt**: Unexpected visual in first 0.5s (e.g. dramatic before/after)
- **Curiosity Gap**: "The reason your shoes look dirty isn't what you think"
- **Value First**: Lead with result, explain later
- **Identity Hook**: "If you own more than 3 pairs of sneakers..."
- **Trending Audio**: Script annotation for recommended sound

### Script Structure Templates (TikTok-optimized)
- **Contrast Burst** (15-30s): Hook(3s) → Reveal(5s) → Detail(10s) → CTA(5s)
- **Educational Loop** (30-60s): Hook(3s) → Problem(5s) → Solution(15s) → Proof(10s) → CTA(5s)
- **Story Arc** (45-90s): Setup → Conflict → Resolution → Lesson → CTA

### TikTok Shop Integration
- Auto-detect product mentions and suggest Shopping tab links
- Generate compliant product claims (FTC guidelines)
- Optimize CTA for Shop conversion ("Tap the yellow bag" vs "Link in bio")

---

## 5. Development Phases (AI-Augmented SDLC)

- [x] PRD Document (this file)
- [x] Multi-agent architecture design
- [x] Backend: FastAPI + SSE streaming + 5 agents
- [ ] Frontend: English UI, real-time streaming, mobile PWA
- [ ] TikTok platform adaptation (Shop, trending sounds, hashtag engine)
- [ ] Demo video + competition submission

---

*PRD Version: 3.0-tiktok | Last Updated: 2026-06-21*
