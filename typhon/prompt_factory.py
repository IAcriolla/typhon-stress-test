#!/usr/bin/env python3
"""
prompt_factory.py — Synthetic prompt generation for context-filling benchmarks.

The context_sweep benchmarks need prompts that actually fill the target context
window. A 50-token prompt sent to a server configured for 8K context does not
measure 8K context performance — it measures 50-token performance with headroom.

build_context_prompt(target_tokens) generates a prompt sized to consume
approximately target_tokens of input, leaving room for the model to generate
a real response. The prompt ends with a question so generation is not trivial.

Token estimation: ~3.8 chars/token for English prose (conservative).
"""

# Characters per token — conservative estimate for English prose.
# Real tokenizers vary. We err slightly low so we don't overflow the context.
CHARS_PER_TOKEN = 3.8

_PROSE = (
    "Artificial intelligence has transformed how humans interact with machines. "
    "Large language models trained on internet-scale text corpora can perform summarization, "
    "translation, code generation, reasoning, and question answering at a high level of quality. "
    "The architecture behind most modern LLMs is the transformer, introduced in 2017. "
    "Transformers use self-attention so every token can attend to every other token in the sequence, "
    "enabling rich contextual representations regardless of distance in the text. "
    "Scaling these architectures to billions of parameters with carefully curated training data "
    "yields emergent capabilities that were not explicitly programmed. "
    "As context windows grow from thousands to hundreds of thousands of tokens, "
    "models can reason over entire codebases, books, and legal documents in a single pass. "
    "Prefill time — the time to process the entire input before generating the first output token — "
    "scales roughly linearly with input length for standard attention implementations, "
    "though flash attention and paged KV caches reduce memory pressure significantly. "
    "KV cache VRAM scales as: layers × heads × head_dim × sequence_length × 2 × dtype_bytes. "
    "For a typical 8B model (32 layers, 32 heads, 128 head_dim, float16), "
    "the KV cache at 128K tokens is approximately 4 GB on top of model weights. "
    "At 256K tokens it doubles to roughly 8 GB. "
    "GPU utilization, thermal output, and memory bandwidth all tell different parts of the story. "
    "A high TPS with low GPU utilization often indicates a CPU or memory bottleneck. "
    "A declining TPS curve as context grows reflects the quadratic cost of attention over long sequences. "
    "Flash attention reduces this to near-linear memory usage while preserving mathematical equivalence. "
)


def build_context_prompt(target_tokens: int) -> str:
    """
    Build a synthetic prompt that fills approximately target_tokens of input.

    The prompt has a fixed header, a repeated prose body, and a short question
    at the end — so the model always has something meaningful to generate.

    Args:
        target_tokens: Desired number of input tokens. The actual prompt will
                       be within ~5% of this value due to tokenizer variance.

    Returns:
        A string prompt ready to send as the user message.
    """
    target_chars = int(target_tokens * CHARS_PER_TOKEN)

    header = (
        f"The following is a technical document about AI and machine learning systems. "
        f"Read it carefully.\n\n"
        "--- BEGIN DOCUMENT ---\n\n"
    )
    footer = (
        "\n\n--- END DOCUMENT ---\n\n"
        "Based on the document above, what is the single most important factor "
        "affecting LLM inference performance at large context sizes?"
    )

    body_budget = target_chars - len(header) - len(footer)
    if body_budget <= 0:
        return header + footer

    reps = (body_budget // len(_PROSE)) + 1
    body = (_PROSE * reps)[:body_budget]

    return header + body + footer


def estimated_tokens(prompt: str) -> int:
    """Return a rough token estimate for a prompt string."""
    return int(len(prompt) / CHARS_PER_TOKEN)
