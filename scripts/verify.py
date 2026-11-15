import logging
import sys
from collections import Counter
from difflib import SequenceMatcher

import httpx
from catalog import PAPERS_PATH, Paper, load_papers, title_key
from sources import link_problem, openalex_work_by_doi

logger = logging.getLogger(__name__)

MIN_TITLE_SIMILARITY = 0.9


def doi_problem(paper: Paper, doi: str) -> str | None:
    try:
        work = openalex_work_by_doi(doi)
    except httpx.HTTPStatusError as error:
        return f"DOI {doi} not found in OpenAlex (HTTP {error.response.status_code})"
    similarity = SequenceMatcher(None, title_key(paper.title), title_key(work.title or "")).ratio()
    if similarity < MIN_TITLE_SIMILARITY:
        return f"DOI {doi} resolves to a different title: {work.title!r}"
    return None


def problems_of(paper: Paper) -> list[str]:
    problems = [doi_problem(paper, paper.doi) if paper.doi else link_problem(str(paper.url))]
    problems += [link_problem(str(link)) for link in (paper.code, paper.data, paper.demo) if link]
    return [problem for problem in problems if problem]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    papers = load_papers(PAPERS_PATH)

    duplicates = [key for key, count in Counter(title_key(p.title) for p in papers).items() if count > 1]
    report = [f"- Duplicate title: {key}" for key in duplicates]
    for paper in papers:
        logger.info("checking %s", paper.title)
        report += [f"- {paper.title}: {problem}" for problem in problems_of(paper)]

    if report:
        sys.stdout.write("## Verification problems\n\n" + "\n".join(report) + "\n")
        sys.exit(1)
    sys.stdout.write(f"All {len(papers)} papers verified: DOIs match their titles, links resolve, no duplicates.\n")


if __name__ == "__main__":
    main()
