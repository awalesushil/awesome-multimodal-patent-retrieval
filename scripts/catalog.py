import re
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, HttpUrl

ROOT = Path(__file__).resolve().parent.parent
PAPERS_PATH = ROOT / "data" / "papers.yaml"
CANDIDATES_PATH = ROOT / "data" / "candidates.yaml"
SEEN_PATH = ROOT / "data" / "seen.yaml"

Category = Literal[
    "surveys",
    "image-retrieval",
    "multimodal-search",
    "figure-understanding",
    "chemical-structures",
    "vlms",
    "datasets",
    "tools",
]

CATEGORY_HEADINGS: dict[Category, str] = {
    "surveys": "Surveys",
    "image-retrieval": "Patent Image Retrieval",
    "multimodal-search": "Multimodal Prior-Art Search",
    "figure-understanding": "Patent Figure Classification and Understanding",
    "chemical-structures": "Chemical Structures in Patents",
    "vlms": "Vision-Language Models for Patents",
    "datasets": "Datasets and Benchmarks",
    "tools": "Tools and Demos",
}


class Paper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    authors: list[str]
    venue: str
    year: int
    category: Category
    url: HttpUrl
    doi: str | None = None
    arxiv: str | None = None
    code: HttpUrl | None = None
    data: HttpUrl | None = None
    demo: HttpUrl | None = None
    added: date


CHECKLIST_ITEM = re.compile(r"^- \[(?P<mark>[ xX])\] .*`(?P<category>[^`]+)`.*<!-- (?P<key>.+?) -->\s*$")


def title_key(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def checklist_item(paper: Paper) -> str:
    return f"- [x] **{paper.title}** ({paper.venue} {paper.year}) `{paper.category}` [link]({paper.url}) <!-- {title_key(paper.title)} -->"


def load_papers(path: Path) -> list[Paper]:
    return [Paper.model_validate(entry) for entry in yaml.safe_load(path.read_text()) or []]


def save_papers(path: Path, papers: list[Paper]) -> None:
    entries = [paper.model_dump(mode="json", exclude_none=True) for paper in papers]
    path.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=1000))


def load_seen() -> set[str]:
    return set(yaml.safe_load(SEEN_PATH.read_text()) or [])


def save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(yaml.safe_dump(sorted(seen), allow_unicode=True, width=1000))
