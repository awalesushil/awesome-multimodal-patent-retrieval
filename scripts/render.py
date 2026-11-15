import csv

from catalog import CATEGORY_HEADINGS, PAPERS_PATH, ROOT, Paper, load_papers

RECENT_FROM = 2015

HEADER = """# Awesome Multimodal Patent Retrieval [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

Research, datasets and tools for searching and understanding patent drawings with images and text, from sketch-based prior-art search to vision-language models for patents.

All papers are also available as a searchable table in [data/papers.csv](data/papers.csv).
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


def section_body(papers: list[Paper]) -> str:
    recent = [paper for paper in papers if paper.year >= RECENT_FROM]
    older = [paper for paper in papers if paper.year < RECENT_FROM]
    parts = [table(recent)] if recent else []
    if older:
        summary = f"Earlier work, before {RECENT_FROM} ({len(older)} papers)"
        parts.append(f"<details>\n<summary>{summary}</summary>\n\n{table(older)}\n\n</details>")
    return "\n\n".join(parts) if parts else "No entries yet."


def render(papers: list[Paper]) -> str:
    by_category = {category: [p for p in papers if p.category == category] for category in CATEGORY_HEADINGS}
    contents = "\n".join(
        f"- [{heading}](#{anchor(heading)}) ({len(by_category[category])})"
        for category, heading in CATEGORY_HEADINGS.items()
    )
    sections = [
        f"## {heading}\n\n{section_body(by_category[category])}\n" for category, heading in CATEGORY_HEADINGS.items()
    ]
    return "\n".join([HEADER, "## Contents\n", contents + "\n", *sections, FOOTER])


CSV_COLUMNS = ["section", "title", "authors", "venue", "year", "url", "doi", "arxiv", "code", "data", "demo", "added"]


def write_csv(papers: list[Paper]) -> None:
    order = list(CATEGORY_HEADINGS)
    rows = sorted(papers, key=lambda p: (order.index(p.category), -p.year, p.title.lower()))
    with (ROOT / "data" / "papers.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for paper in rows:
            entry = paper.model_dump(mode="json")
            entry["section"] = CATEGORY_HEADINGS[paper.category]
            entry["authors"] = "; ".join(paper.authors)
            writer.writerow({column: entry[column] or "" for column in CSV_COLUMNS})


def main() -> None:
    papers = load_papers(PAPERS_PATH)
    (ROOT / "README.md").write_text(render(papers))
    write_csv(papers)


if __name__ == "__main__":
    main()
