import html
import logging
import re
import sys
from datetime import date

from catalog import (
    CANDIDATES_PATH,
    CATEGORY_HEADINGS,
    PAPERS_PATH,
    Category,
    Paper,
    checklist_item,
    load_papers,
    load_seen,
    save_papers,
    save_seen,
    title_key,
)
from sources import (
    VenuePaper,
    Work,
    ceur_papers,
    ceur_volumes,
    dblp_papers,
    dblp_venue,
    link_problem,
    openalex_work_by_doi,
    openalex_works,
)

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    '"patent drawing"',
    '"patent image"',
    '"patent figure"',
    '"design patent" image',
    "patent sketch retrieval",
    'patent "vision-language"',
    "patent multimodal retrieval",
    "patent Markush structure recognition",
    'patent "chemical structure" image',
    'patent "circuit diagram"',
    'patent "engineering drawing"',
    'patent "technical drawing"',
    "patent flowchart recognition",
    '"industrial design" image retrieval',
]
WORLD_PATENT_INFORMATION = "S84022812"
WPI_QUERY = "(image OR drawing OR figure OR visual OR multimodal OR sketch OR diagram OR flowchart OR chemical)"
DBLP_PATENT_VENUES = {
    "PatentSemTech": "?paper dblp:publishedInStream <https://dblp.org/streams/conf/patentsemtech> .",
    "PaIR@CIKM": "?paper dblp:publishedInStream <https://dblp.org/streams/conf/pair> .",
    "CLEF-IP": '?paper dblp:publishedInStream <https://dblp.org/streams/conf/clef> . FILTER(REGEX(?title, "patent", "i"))',
    "NTCIR": '?paper dblp:publishedInStream <https://dblp.org/streams/conf/ntcir> . FILTER(REGEX(?title, "patent", "i"))',
    "Current Challenges in Patent IR": '?paper dblp:publishedIn "Current Challenges in Patent Information Retrieval" .',
}
CEUR_PATENT_VOLUMES = re.compile(r"\bpatent", re.IGNORECASE)
SEARCH_PAGES = 3
CITATION_PAGES = 2
SKIPPED_TYPES = {"book", "paratext", "erratum", "retraction", "editorial", "letter", "peer-review", "other"}

PATENT = re.compile(r"\bpatent", re.IGNORECASE)
VISUAL = re.compile(
    r"\b(imag\w*|drawings?|figures?|sketch\w*|visual\w*|multi-?modal\w*|vision|photo\w*|diagrams?|flowcharts?|schematics?|markush|clip|cad)\b",
    re.IGNORECASE,
)
METHOD = re.compile(
    r"\b(retriev\w*|search\w*|classif\w*|recogni\w*|detect\w*|segment\w*|caption\w*|learning|neural|deep|"
    r"dataset|benchmark|embedding\w*|similarity|matching|model\w*|transformer\w*|convolutional)\b",
    re.IGNORECASE,
)
CHEMICAL_STRUCTURE = re.compile(r"\b(chemical[- ]structures?|markush|molecul\w*)\b", re.IGNORECASE)
MEDICAL = re.compile(
    r"\b(foramen|ductus|coronary|arter\w*|stents?|aneurysm|patients?|clinical|surg\w*|catheter\w*|cardi\w*)\b",
    re.IGNORECASE,
)
CATEGORY_RULES: list[tuple[Category, re.Pattern[str]]] = [
    ("surveys", re.compile(r"\b(survey|review|overview)\b", re.IGNORECASE)),
    (
        "chemical-structures",
        re.compile(r"\b(chemical|chemistry|markush|molecul\w*|smiles|ocsr|compounds?)\b", re.IGNORECASE),
    ),
    ("datasets", re.compile(r"\b(dataset|benchmark|corpus|test collection)\b", re.IGNORECASE)),
    ("vlms", re.compile(r"\b(vision-language|vlms?|lvlms?|clip|large language|llms?|gpt\w*)\b", re.IGNORECASE)),
    (
        "figure-understanding",
        re.compile(
            r"\b(classif\w*|caption\w*|question answering|vqa|recogni\w*|segment\w*|flowcharts?|understanding)\b",
            re.IGNORECASE,
        ),
    ),
    ("multimodal-search", re.compile(r"\b(multi-?modal|cross-modal|prior[- ]art|text and image)\b", re.IGNORECASE)),
    ("tools", re.compile(r"\b(demo\w*|system|tool|interactive|platform|interface)\b", re.IGNORECASE)),
]


def clean_title(title: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", title)).split())


def in_scope(work: Work) -> bool:
    title = work.title or ""
    text = f"{title} {work.abstract}"
    about_patents = bool(PATENT.search(title)) or len(PATENT.findall(work.abstract)) >= 2
    visual = bool(VISUAL.search(title)) or len(VISUAL.findall(work.abstract)) >= 2
    specific_title = any(pattern.search(title) for pattern in (PATENT, VISUAL, METHOD))
    return about_patents and visual and specific_title and bool(METHOD.search(text)) and not MEDICAL.search(title)


def guess_category(title: str) -> Category:
    for category, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return category
    return "image-retrieval"


def paper_url(work: Work) -> str | None:
    if work.doi:
        return work.doi
    if work.arxiv_id:
        return f"https://arxiv.org/abs/{work.arxiv_id}"
    return work.primary_location.landing_page_url if work.primary_location else None


def venue_of(work: Work, title: str) -> str:
    venue = dblp_venue(work.bare_doi, title)
    if venue:
        return venue
    source = work.primary_location.source if work.primary_location else None
    if source and source.display_name:
        return source.display_name
    return "arXiv" if work.arxiv_id else "Unknown venue"


def to_paper(work: Work, today: date) -> Paper | None:
    url = paper_url(work)
    if url is None or not work.title:
        return None
    if not work.doi and (problem := link_problem(url)):
        logger.info("skipping until its link works: %s", problem)
        return None
    title = clean_title(work.title)
    return Paper(
        title=title,
        authors=[authorship.author.display_name for authorship in work.authorships],
        venue=venue_of(work, title),
        year=work.publication_year,
        category=guess_category(title),
        url=url,
        doi=work.bare_doi,
        arxiv=work.arxiv_id,
        added=today,
    )


def fetch_works(papers: list[Paper]) -> list[Work]:
    works: list[Work] = []
    for query in SEARCH_QUERIES:
        logger.info("searching %s", query)
        works += openalex_works(f"title_and_abstract.search:{query}", SEARCH_PAGES)

    logger.info("searching World Patent Information")
    works += openalex_works(
        f"primary_location.source.id:{WORLD_PATENT_INFORMATION},title_and_abstract.search:{WPI_QUERY}", SEARCH_PAGES
    )

    for paper in papers:
        if paper.doi:
            logger.info("citations of %s", paper.title)
            seed_id = openalex_work_by_doi(paper.doi).id.rsplit("/", 1)[1]
            works += openalex_works(f"cites:{seed_id}", CITATION_PAGES)
    return works


def venue_paper(found: VenuePaper, today: date) -> Paper | None:
    title = re.sub(r"\s+\d+-\d+$", "", found.title)
    url = f"https://doi.org/{found.doi}" if found.doi else found.url
    if not (VISUAL.search(title) or CHEMICAL_STRUCTURE.search(title)) or MEDICAL.search(title) or url is None:
        return None
    if not found.doi and (problem := link_problem(url)):
        logger.info("skipping until its link works: %s", problem)
        return None
    clef_year = re.search(r"CLEF(\d{4})", url)
    return Paper(
        title=title,
        authors=found.authors,
        venue=found.venue,
        year=int(clef_year[1]) if clef_year else found.year,
        category=guess_category(title),
        url=url,
        doi=found.doi,
        added=today,
    )


def patent_venue_papers(seen: set[str], today: date) -> list[Paper]:
    found: list[VenuePaper] = []
    for name, match in DBLP_PATENT_VENUES.items():
        logger.info("listing %s in DBLP", name)
        found += dblp_papers(match)
    for volume in ceur_volumes(CEUR_PATENT_VOLUMES):
        logger.info("listing CEUR %s", volume)
        found += ceur_papers(volume)

    added: dict[str, Paper] = {}
    for candidate in found:
        key = title_key(re.sub(r"\s+\d+-\d+$", "", candidate.title))
        if key in seen or key in added:
            continue
        if paper := venue_paper(candidate, today):
            added[key] = paper
    return list(added.values())


def new_candidates(works: list[Work], seen: set[str]) -> dict[str, Work]:
    candidates: dict[str, Work] = {}
    for work in works:
        if not work.title or work.type in SKIPPED_TYPES or not in_scope(work):
            continue
        key = title_key(clean_title(work.title))
        if key in seen:
            continue
        if key not in candidates or (candidates[key].type == "preprint" and work.type != "preprint"):
            candidates[key] = work
    return candidates


def summary(added: list[Paper]) -> str:
    if not added:
        return "No new candidates this week.\n"
    categories = ", ".join(f"`{category}`" for category in CATEGORY_HEADINGS)
    return "\n".join(
        [
            f"## {len(added)} new candidates",
            "",
            (
                "Untick papers to reject and edit the category in backticks where it is wrong, then merge. "
                "The daily publish job applies this list; rejected papers are not suggested again."
            ),
            "",
            f"Categories: {categories}",
            "",
            *map(checklist_item, added),
            "",
        ]
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    papers = load_papers(PAPERS_PATH)
    pending = load_papers(CANDIDATES_PATH)
    seen = load_seen() | {title_key(paper.title) for paper in papers + pending}

    candidates = new_candidates(fetch_works(papers), seen)
    today = date.today()
    added = [paper for work in candidates.values() if (paper := to_paper(work, today))]
    added += patent_venue_papers(seen | {title_key(paper.title) for paper in added}, today)

    save_papers(CANDIDATES_PATH, pending + added)
    save_seen(seen | {title_key(paper.title) for paper in added})
    sys.stdout.write(summary(added))


if __name__ == "__main__":
    main()
