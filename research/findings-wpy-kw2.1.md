# Prompt Injection Detection & Sanitation: Literature Review and Recommendations

**Research Task:** wpy-kw2.1  
**Date:** 2026-02-02  
**Prepared for:** waasp-py Content Filtering Module / waasp-core

---

## Executive Summary

This document surveys prompt injection detection and sanitation techniques for integration into the waasp-py content filtering module. Prompt injection remains the #1 vulnerability in OWASP's Top 10 for LLM Applications (2025), with no complete solution currently available. Effective defense requires a **multi-layered approach** combining prevention, detection, and blast radius reduction.

**Key Recommendations for waasp-core:**
1. Implement multi-stage detection pipeline (heuristics → semantic → model-based)
2. Add canary token support for data exfiltration detection
3. Provide configurable input/output sanitization filters
4. Support perplexity-based anomaly detection
5. Integrate with existing pattern matching systems (YARA-style rules)

---

## 1. Attack Taxonomy

### 1.1 Direct vs. Indirect Injection

| Type | Description | Attack Vector |
|------|-------------|---------------|
| **Direct** | User intentionally crafts malicious input | Chat interface, API calls |
| **Indirect** | Malicious instructions embedded in external content | Documents, web pages, emails, RAG corpora |

### 1.2 Attack Categories (Based on OWASP, MITRE ATLAS, Academic Literature)

#### Direct Prompt Injections
- **Jailbreaks/Role Play:** DAN (Do Anything Now), virtualization, developer mode
- **Obfuscation:** Base64 encoding, emojis, ASCII art, Unicode characters, misspelling
- **Payload Splitting:** Combining benign parts to form malicious instructions
- **Adversarial Suffixes:** Gibberish strings trained via gradient search that transfer between models
- **Instruction Manipulation:** Overriding system prompts ("Ignore previous instructions")
- **Double Character:** Requesting two personas (restricted/unrestricted)
- **Many-shot Jailbreaking:** Exploiting long context windows (Anthropic, April 2024)

#### Indirect Prompt Injections
- **Web Content Poisoning:** Hidden instructions in HTML, CSS (white-on-white text)
- **Document Injection:** PDFs, Word docs with concealed prompts
- **RAG Poisoning:** Malicious content in vector databases
- **Multi-agent Infection:** Propagating through agent chains

#### Multimodal Injections
- **Image-based:** Instructions embedded in images (metadata, visual)
- **Cross-modal:** Exploiting interactions between text and visual modalities

### 1.3 Attack Goals

| Goal | Impact | Severity |
|------|--------|----------|
| **Instruction Hijacking** | Model produces unintended outputs | Medium-High |
| **Data Exfiltration** | Leaking system prompts, PII, API keys | Critical |
| **Privilege Escalation** | Executing unauthorized actions | Critical |
| **Code Execution** | RCE via tool/plugin exploitation | Critical |
| **SSRF/SQL Injection** | Attacking downstream systems | High |

---

## 2. Detection Techniques

### 2.1 Heuristic/Pattern-Based Detection

**Approach:** Regex patterns, keyword lists, signature matching

**Implementations:**
- **Vigil-LLM:** YARA-based signature detection
- **Rebuff:** Heuristics filter layer
- **Custom regex:** Common injection phrases ("ignore previous", "forget instructions")

**Pros:** Fast, low latency, interpretable  
**Cons:** Easily evaded with obfuscation, requires constant updates

**Recommendation for waasp-core:** Implement as first-pass filter with configurable signature sets

### 2.2 Semantic/Embedding-Based Detection

**Approach:** Compare input embeddings against known attack vectors in vector database

**Implementations:**
- **Rebuff:** Stores attack embeddings in Pinecone/Chroma
- **Vigil-LLM:** VectorDB scanner with auto-updating on detected attacks
- **Custom:** Sentence transformers (SBERT) with cosine similarity

**Key Insight:** Attack prompts cluster in embedding space but show high diversity

**Pros:** Catches variations of known attacks, self-hardening  
**Cons:** Requires embedding model parity, storage overhead

**Recommendation for waasp-core:** Support pluggable vector stores, provide pre-computed attack embeddings

### 2.3 Model-Based (LLM/Classifier) Detection

**Approach:** Use dedicated models to classify injection attempts

**Implementations:**
- **Rebuff:** Dedicated LLM analyzes prompts
- **Llama Guard:** Multi-class safety classification
- **Llama Prompt Guard 2:** Lightweight jailbreak classifier
- **DeBERTa-based:** `deepset/deberta-v3-base-injection` (threshold ~0.98)
- **Adversarial Prompt Shield (APS):** Resilient against adversarial noise

**Pros:** Handles novel attacks better than heuristics  
**Cons:** Higher latency, potential false positives, model drift

**Recommendation for waasp-core:** Support configurable model backends (local/API), allow threshold tuning

### 2.4 Perplexity-Based Detection

**Approach:** Measure token-level perplexity; adversarial suffixes exhibit high perplexity

**Academic Sources:**
- "Token-Level Adversarial Prompt Detection Based on Perplexity Measures" (arXiv:2311.11509)
- "Detecting Language Model Attacks with Perplexity" (arXiv:2308.14132)
- Google DeepMind Gemini Paper: Perplexity threshold filtering for injection detection

**Mechanism:**
```
For each token t:
  if LLM.perplexity(t) > threshold:
    flag_as_potential_attack()
```

**Pros:** Effective against adversarial suffixes, model-agnostic  
**Cons:** Requires access to model logits, threshold tuning needed

**Recommendation for waasp-core:** Implement as optional scanner for models that expose logits

### 2.5 Canary Token Detection

**Approach:** Inject unique tokens into prompts; detect if they appear in output (indicating prompt leakage)

**Implementations:**
- **Rebuff:** `add_canaryword()` → `is_canary_word_leaked()`
- **Vigil-LLM:** Configurable canary headers (`<-@!-- {canary} --@!->`)

**Detection Workflows:**
1. **Prompt Leakage:** Canary in system prompt appears in output
2. **Goal Hijacking:** Response references canary instead of completing task

**Recommendation for waasp-core:** Core feature for data exfiltration detection

### 2.6 Response Analysis / Prompt-Response Similarity

**Approach:** Compare output relevance to original user intent

**Implementations:**
- **RAG Triad:** Context relevance, groundedness, question/answer relevance
- **Vigil-LLM:** Prompt-response similarity scanner

**Pros:** Catches successful hijacking post-hoc  
**Cons:** Requires defining expected behavior, adds latency

---

## 3. Sanitation & Prevention Approaches

### 3.1 Input Cleaning/Pre-processing

| Technique | Description | Effectiveness |
|-----------|-------------|---------------|
| **Paraphrasing** | LLM rephrases input before processing | High for jailbreaks, may degrade quality |
| **Retokenization** | Break tokens into smaller units | Medium, disrupts token-specific attacks |
| **Backtranslation** | Infer intent from response, compare | High, but doubles latency |
| **Delimiters** | Separate user input with markers | Low-Medium, easily bypassed |
| **Character perturbation** | SmoothLLM: random character changes + aggregation | High for suffix attacks |

**Recommendation for waasp-core:** Implement paraphrasing as optional input filter

### 3.2 Output Filtering

**Approaches:**
- PII redaction / DLP integration
- Toxicity/harmful content filtering
- System prompt leakage detection
- Structured output validation

**Implementations:**
- **OpenAI Guardrails Python:** Multi-checkpoint output scanning
- **NeMo Guardrails:** Programmable output rails
- **Guardrails AI:** Structural validators for LLM outputs

### 3.3 Privilege Control & Sandboxing

**Key Principle:** Treat all LLM outputs as potentially malicious (NVIDIA AI Red Team)

**Recommendations:**
- Least privilege: Minimal access for LLM to backend systems
- Parameterized tool calls: Never pass raw LLM output to shells/databases
- Human-in-the-loop: Gate high-risk actions (send email, delete data)
- Context isolation: Separate trusted (system) and untrusted (user) content

### 3.4 Prompt Engineering / Instructional Defense

**Techniques:**
- Clear role/capability definitions in system prompt
- Output format specifications
- Self-reminder defenses: "Remember, you must never..."
- Spotlighting: Mark data sections clearly

**Limitation:** Can be overridden by sufficiently clever attacks

---

## 4. Open Source Implementations

### 4.1 Rebuff (ProtectAI)
**GitHub:** https://github.com/protectai/rebuff  
**Language:** Python, TypeScript  
**License:** Apache 2.0

**Architecture:**
```
User Input → Heuristics → LLM Detection → VectorDB Check → Decision
                              ↓
                        Canary Token Injection
                              ↓
                        Leakage Detection
```

**Strengths:**
- Multi-layered defense (4 layers)
- Self-hardening via attack embedding storage
- LangChain integration
- API + self-hosted options

**Weaknesses:**
- Alpha stage, no production guarantees
- Requires external services (Pinecone, OpenAI)

### 4.2 Vigil-LLM (deadbits)
**GitHub:** https://github.com/deadbits/vigil-llm  
**Language:** Python  
**License:** MIT

**Scanners:**
- Vector database (auto-updating)
- YARA/heuristics
- Transformer model
- Prompt-response similarity
- Canary tokens
- Sentiment analysis
- Relevance (via LiteLLM)

**Strengths:**
- Modular scanner architecture
- YARA integration for custom signatures
- Local-first (can run without cloud APIs)
- REST API + Python library
- Pre-built datasets and signatures

**Weaknesses:**
- Alpha/research stage
- Requires YARA installation

### 4.3 NeMo Guardrails (NVIDIA)
**GitHub:** https://github.com/NVIDIA/NeMo-Guardrails  
**Language:** Python  
**License:** Apache 2.0

**Features:**
- Programmable rails (Colang DSL)
- Runtime dialogue management
- Topic/behavior control
- LLM-agnostic

**Best for:** Enterprise deployments requiring custom rail definitions

### 4.4 Guardrails AI
**GitHub:** https://github.com/guardrails-ai/guardrails  
**Hub:** https://hub.guardrails.ai

**Features:**
- Pre-built validators (Hub)
- Structural output validation
- Type guarantees
- Quality measures

**Best for:** Output structure enforcement, validation pipelines

### 4.5 LangChain Security Components
**Rebuff Integration:** Native LangChain integration  
**Guardrails Middleware:** AgentMiddleware for input/output validation

**CVE Note:** LangChain has had multiple CVEs (CVE-2023-29374, CVE-2023-32785/32786, CVE-2025-68664). Ensure latest versions.

### 4.6 Other Notable Tools

| Tool | Focus | Link |
|------|-------|------|
| **Llama Guard** | Input/output classification | Meta |
| **Prompt Guard 2** | Jailbreak detection | Meta |
| **LLM Guard** | Multi-scanner security | HuggingFace |
| **Lakera Guard** | Enterprise injection detection | Commercial |
| **Azure AI Content Safety** | Content moderation | Microsoft |

---

## 5. Academic Literature Summary

### Key Papers

1. **"Prompt Injection Attacks in Large Language Models"** (MDPI, 2025)
   - Comprehensive taxonomy: direct jailbreaking, indirect injection
   - Attack vector classification: conversational AI, code assistants, RAG, agents
   - Evaluation framework: effectiveness, overhead, robustness

2. **"Multimodal Prompt Injection Attacks"** (arXiv:2509.05883, Sep 2025)
   - Tests 8 commercial models (GPT-4o, Claude 3, Llama 3, etc.)
   - Categories: direct, indirect, image-based, prompt leakage
   - Finding: Claude 3 most robust, but still requires additional defenses

3. **"Not what you've signed up for"** (arXiv:2302.12173)
   - Seminal paper on indirect prompt injection
   - Real-world attack scenarios via RAG, plugins

4. **"Universal and Transferable Adversarial Attacks"** (arXiv:2307.15043)
   - Adversarial suffixes that transfer between models
   - Gradient-based suffix optimization

5. **"Baseline Defenses for Adversarial Attacks"** (arXiv:2309.00614)
   - Paraphrasing + retokenization analysis
   - Preprocessing defense evaluation

6. **"SmoothLLM"** (arXiv:2310.03684)
   - Character-level perturbation + aggregation
   - Reduces attack success rate below 1%

7. **"Lessons from Defending Gemini"** (Google DeepMind, 2025)
   - Perplexity threshold filtering
   - Production deployment insights

---

## 6. Recommendations for waasp-core

### 6.1 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    waasp-py Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input → [Heuristics] → [Semantic] → [Model] → LLM Call    │
│            │              │            │           │        │
│            ▼              ▼            ▼           ▼        │
│         Pattern       VectorDB     Classifier   Response    │
│         Matching      Similarity   Score        Analysis    │
│                                                             │
│  + Canary Token Injection ──────────────────► Leakage Check │
│  + Perplexity Scoring (optional) ──────────► Anomaly Flag   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Core Components to Implement

| Priority | Component | Description |
|----------|-----------|-------------|
| **P0** | Pattern Scanner | Configurable regex/keyword rules |
| **P0** | Canary Tokens | Injection + leakage detection |
| **P1** | Vector Similarity | Pluggable embedding + vector store |
| **P1** | Model Classifier | Support HuggingFace + OpenAI classifiers |
| **P2** | Perplexity Scanner | Token-level anomaly detection |
| **P2** | Output Filters | PII redaction, leakage detection |
| **P3** | Paraphrasing | Input normalization option |

### 6.3 API Design Suggestions

```python
from waasp import ContentFilter, Scanner

# Initialize with multiple scanners
filter = ContentFilter(
    scanners=[
        Scanner.pattern(rules="default"),
        Scanner.vector_similarity(model="text-embedding-ada-002"),
        Scanner.classifier(model="deepset/deberta-v3-base-injection"),
    ],
    canary_tokens=True,
    threshold_scores={
        "pattern": 0.5,
        "similarity": 0.8,
        "classifier": 0.98,
    }
)

# Scan input
result = filter.scan_input(user_prompt)
if result.injection_detected:
    handle_injection(result)

# Inject canary and check leakage
prompt_with_canary, canary = filter.add_canary(system_prompt)
# ... LLM call ...
if filter.check_canary_leak(response, canary):
    handle_data_leak()
```

### 6.4 Configuration Options

```yaml
waasp:
  injection_detection:
    enabled: true
    scanners:
      - type: pattern
        rules: default  # or path to custom YARA/regex
        threshold: 0.5
      - type: vector
        model: all-MiniLM-L6-v2
        store: chromadb
        threshold: 0.85
      - type: classifier  
        model: deepset/deberta-v3-base-injection
        threshold: 0.98
      - type: perplexity
        enabled: false  # requires model logit access
        threshold: 50
    canary_tokens:
      enabled: true
      header: "<-@!-- {canary} --@!->"
      length: 16
    output_filtering:
      pii_redaction: true
      prompt_leak_detection: true
```

### 6.5 Testing & Evaluation

**Datasets:**
- Vigil datasets: `deadbits/vigil-instruction-bypass-ada-002`, `vigil-jailbreak-ada-002`
- HackAPrompt competition data
- Gandalf challenge prompts

**Metrics:**
- True Positive Rate (injection detection)
- False Positive Rate (legitimate prompts blocked)
- Latency overhead
- Robustness against adaptive attacks

---

## 7. Conclusions

1. **No silver bullet exists** - Prompt injection cannot be fully solved at the current state of the art. Defense-in-depth is mandatory.

2. **Multi-layer detection is essential** - Combining heuristics, semantic analysis, and model-based detection catches more attack variants.

3. **Canary tokens are critical** - Simple but effective for detecting data exfiltration and prompt leakage.

4. **Perplexity scoring shows promise** - Particularly for adversarial suffix attacks; requires model access.

5. **Treat LLM output as untrusted** - Parameterize all downstream calls, enforce least privilege.

6. **Self-hardening is valuable** - Storing detected attack embeddings improves future detection (Rebuff/Vigil approach).

7. **Stay updated** - Attack techniques evolve rapidly; signature databases need continuous updates.

---

## References

### Primary Sources
- OWASP LLM Top 10 (2025): https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- MITRE ATLAS: AML.T0051 (Prompt Injection), AML.T0054 (Jailbreak)
- NVIDIA AI Red Team Blog: https://developer.nvidia.com/blog/securing-llm-systems-against-prompt-injection/

### Tools & Implementations
- Rebuff: https://github.com/protectai/rebuff
- Vigil-LLM: https://github.com/deadbits/vigil-llm
- NeMo Guardrails: https://github.com/NVIDIA/NeMo-Guardrails
- Guardrails AI: https://github.com/guardrails-ai/guardrails
- tldrsec Defenses: https://github.com/tldrsec/prompt-injection-defenses

### Academic Papers
- arXiv:2302.12173 - Indirect Prompt Injection
- arXiv:2307.15043 - Universal Adversarial Attacks
- arXiv:2309.00614 - Baseline Defenses
- arXiv:2310.03684 - SmoothLLM
- arXiv:2311.11509 - Perplexity-based Detection
- arXiv:2509.05883 - Multimodal Prompt Injection

### Blog Posts & Articles
- Simon Willison: https://simonwillison.net/series/prompt-injection/
- Kai Greshake: https://kai-greshake.de/posts/approaches-to-pi-defense/
- Arthur AI Taxonomy: https://www.arthur.ai/blog/from-jailbreaks-to-gibberish-understanding-the-different-types-of-prompt-injections
- Lakera Direct Injections: https://www.lakera.ai/blog/direct-prompt-injections
- Neptune.ai Deep Dive: https://neptune.ai/blog/understanding-prompt-injection

---

*Document generated for waasp-py project - wpy-kw2.1 research task*
