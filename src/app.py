"""
Gradio interface for The Unofficial Guide — Boston food & restaurant reviews.

Milestone 5 interface. Wraps the RAG pipeline (src/generate.py) in a simple
web UI: the user types a question, the system retrieves review chunks, and a
grounded answer is shown along with the sources it drew from.

Usage:
  python src/app.py
Then open the local URL Gradio prints (default http://127.0.0.1:7860).

Requires GROQ_API_KEY in a .env file (see .env.example) and that
`python src/ingest.py` has been run to produce chunks.jsonl.
"""

from __future__ import annotations

import gradio as gr

from generate import answer

EXAMPLE_QUESTIONS = [
    "What do reviewers say about the wait at Mike's Pastry?",
    "Which neighborhood is best for ramen in Boston?",
    "Is Neptune Oyster's lobster roll worth the price?",
    "Where can I find budget-friendly food in Chinatown?",
    "Any good vegetarian or vegan spots in Cambridge?",
]


def ask(question: str):
    """Return (answer_markdown, sources_markdown) for the UI."""
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""

    result = answer(question)

    answer_md = result["answer"]
    if result["sources"]:
        sources_md = "\n".join(
            f"- **{s['source']}** — `{s['path']}`" for s in result["sources"]
        )
    else:
        sources_md = "_No sources retrieved._"
    return answer_md, sources_md


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="The Unofficial Guide — Boston Food") as demo:
        gr.Markdown(
            "# The Unofficial Guide — Boston Food & Restaurant Reviews\n"
            "Ask about where to eat in Boston. Answers come only from the "
            "collected reviews, with sources listed below."
        )
        with gr.Row():
            question = gr.Textbox(
                label="Your question",
                placeholder="e.g., Which neighborhood is best for ramen?",
                scale=4,
            )
            submit = gr.Button("Ask", variant="primary", scale=1)

        answer_box = gr.Markdown(label="Answer")
        with gr.Accordion("Sources", open=True):
            sources_box = gr.Markdown()

        gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question)

        submit.click(ask, inputs=question, outputs=[answer_box, sources_box])
        question.submit(ask, inputs=question, outputs=[answer_box, sources_box])

    return demo


if __name__ == "__main__":
    build_ui().launch(share=True)
