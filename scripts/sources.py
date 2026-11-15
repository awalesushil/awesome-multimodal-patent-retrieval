import os
import re

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

OPENALEX = "https://api.openalex.org"
DBLP_SPARQL = "https://sparql.dblp.org/sparql"
USER_AGENT = "awesome-multimodal-patent-retrieval (+https://github.com/awalesushil/awesome-multimodal-patent-retrieval)"
BOT_BLOCKED = 403
WORK_FIELDS = "id,doi,title,publication_year,authorships,primary_location,locations,abstract_inverted_index,type"

OPENALEX_KEY = {"api_key": key} if (key := os.environ.get("OPENALEX_API_KEY")) else {}

client = httpx.Client(
    headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json, application/json"},
    timeout=30,
    follow_redirects=True,
)


class Source(BaseModel):
    display_name: str | None = None


class Location(BaseModel):
    landing_page_url: str | None = None
    source: Source | None = None


class Author(BaseModel):
    display_name: str


class Authorship(BaseModel):
    author: Author


class Work(BaseModel):
    id: str
    doi: str | None = None
    title: str | None = None
    publication_year: int
    type: str | None = None
    authorships: list[Authorship]
    primary_location: Location | None = None
    locations: list[Location]
    abstract_inverted_index: dict[str, list[int]] | None = None

    @property
    def abstract(self) -> str:
        if not self.abstract_inverted_index:
            return ""
        positions = {pos: word for word, places in self.abstract_inverted_index.items() for pos in places}
        return " ".join(positions[pos] for pos in sorted(positions))

    @property
    def bare_doi(self) -> str | None:
        return self.doi.removeprefix("https://doi.org/").lower() if self.doi else None

    @property
    def arxiv_id(self) -> str | None:
        for location in self.locations:
            url = location.landing_page_url or ""
            if "arxiv.org/abs/" in url:
                return re.sub(r"v\d+$", "", url.split("arxiv.org/abs/")[1])
        return None


class WorksPage(BaseModel):
    results: list[Work]


def is_transient(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429 or error.response.status_code >= 500
    return isinstance(error, httpx.TransportError)


@retry(
    retry=retry_if_exception(is_transient),
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=2, max=30),
    reraise=True,
)
def get_json(url: str, params: dict[str, str]) -> object:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def link_problem(url: str) -> str | None:
    try:
        status = client.get(url).status_code
    except httpx.TransportError as error:
        return f"{url} unreachable ({type(error).__name__})"
    if status >= 400 and status != BOT_BLOCKED:
        return f"{url} returned HTTP {status}"
    return None


def openalex_work_by_doi(doi: str) -> Work:
    return Work.model_validate(get_json(f"{OPENALEX}/works/doi:{doi}", {"select": WORK_FIELDS, **OPENALEX_KEY}))


def openalex_works(filter_: str, pages: int) -> list[Work]:
    works: list[Work] = []
    for page in range(1, pages + 1):
        params = {"filter": filter_, "select": WORK_FIELDS, "per-page": "100", "page": str(page), **OPENALEX_KEY}
        results = WorksPage.model_validate(get_json(f"{OPENALEX}/works", params)).results
        works.extend(results)
        if len(results) < 100:
            break
    return works


class SparqlValue(BaseModel):
    value: str


class SparqlBinding(BaseModel):
    venue: SparqlValue


class SparqlBindings(BaseModel):
    bindings: list[SparqlBinding]


class SparqlResponse(BaseModel):
    results: SparqlBindings


def dblp_venue(doi: str | None, title: str) -> str | None:
    escaped = title.rstrip(".").replace("\\", "\\\\").replace('"', '\\"')
    matches = [f'dblp:title "{escaped}."']
    if doi:
        matches.insert(0, f"dblp:doi <https://doi.org/{doi}>")
    for match in matches:
        query = f"PREFIX dblp: <https://dblp.org/rdf/schema#> SELECT ?venue WHERE {{ ?paper {match} ; dblp:publishedIn ?venue . }}"
        bindings = SparqlResponse.model_validate(get_json(DBLP_SPARQL, {"query": query})).results.bindings
        if bindings:
            venue = re.sub(r"\s*\(\d+\)$", "", bindings[0].venue.value)
            return "arXiv" if venue == "CoRR" else venue
    return None
