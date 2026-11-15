from catalog import CATEGORY_HEADINGS, PAPERS_PATH, ROOT, Paper, load_papers

HEADER = """# Awesome Multimodal Patent Retrieval [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

Research, datasets and tools for searching and understanding patent drawings with images and text, from sketch-based prior-art search to vision-language models for patents.

> Work in progress: the list is being seeded and will grow over the coming weeks. Suggestions are welcome.
"""

FOOTER = """## Footnotes

- This README is generated from [data/papers.yaml](data/papers.yaml) by [scripts/render.py](scripts/render.py); new papers are suggested weekly from OpenAlex and DBLP and reviewed before merging.
- Text-only patent retrieval and patent data sources: [Awesome Patent Data Mining](https://github.com/mahesh-maan/awesome-patent-retrieval).
- Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
"""


def anchor(heading: str) -> str:
    return heading.lower().replace(" ", "-")


def escape(text: str) -> str:
    return text.replace("|", "\\|")


def authors_cell(authors: list[str]) -> str:
    if len(authors) > 3:
        return f"{authors[0]} et al."
    return ", ".join(authors)


def links_cell(paper: Paper) -> str:
    links = [f"[Paper]({paper.url})"]
    if paper.arxiv and "arxiv.org" not in str(paper.url):
        links.append(f"[arXiv](https://arxiv.org/abs/{paper.arxiv})")
    for label, link in (("Code", paper.code), ("Data", paper.data), ("Demo", paper.demo)):
        if link:
            links.append(f"[{label}]({link})")
    return " ".join(links)


def table(papers: list[Paper]) -> str:
    rows = [["Title", "Authors", "Venue", "Year", "Links"]]
    for paper in sorted(papers, key=lambda p: (-p.year, p.title.lower())):
        text_cells = [f"**{paper.title}**", authors_cell(paper.authors), paper.venue, str(paper.year)]
        rows.append([*map(escape, text_cells), links_cell(paper)])

    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    lines = ["| " + " | ".join(cell.ljust(width) for cell, width in zip(row, widths)) + " |" for row in rows]
    lines.insert(1, "| " + " | ".join("-" * width for width in widths) + " |")
    return "\n".join(lines)


def render(papers: list[Paper]) -> str:
    contents = "\n".join(f"- [{heading}](#{anchor(heading)})" for heading in CATEGORY_HEADINGS.values())
    sections = []
    for category, heading in CATEGORY_HEADINGS.items():
        in_category = [paper for paper in papers if paper.category == category]
        body = table(in_category) if in_category else "No entries yet."
        sections.append(f"## {heading}\n\n{body}\n")

    return "\n".join([HEADER, "## Contents\n", contents + "\n", *sections, FOOTER])


def main() -> None:
    (ROOT / "README.md").write_text(render(load_papers(PAPERS_PATH)))


if __name__ == "__main__":
    main()
