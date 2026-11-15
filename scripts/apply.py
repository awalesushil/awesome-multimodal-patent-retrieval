import logging
import subprocess
import sys

from catalog import CANDIDATES_PATH, CHECKLIST_ITEM, PAPERS_PATH, Category, Paper, load_papers, save_papers, title_key
from pydantic import BaseModel, TypeAdapter

logger = logging.getLogger(__name__)


class PullRequest(BaseModel):
    headRefName: str
    body: str


def merged_candidate_prs() -> list[PullRequest]:
    command = ["gh", "pr", "list", "--state", "merged", "--limit", "20", "--json", "headRefName,body"]
    output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    prs = TypeAdapter(list[PullRequest]).validate_json(output)
    return [pr for pr in prs if pr.headRefName.startswith("candidates/")]


def decisions(body: str) -> dict[str, Category | None]:
    result: dict[str, Category | None] = {}
    for line in body.splitlines():
        match = CHECKLIST_ITEM.match(line.strip())
        if match:
            category = TypeAdapter(Category).validate_python(match["category"])
            result[match["key"]] = category if match["mark"] != " " else None
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    candidates = load_papers(CANDIDATES_PATH)
    if not candidates:
        return

    decided: dict[str, Category | None] = {}
    for pr in merged_candidate_prs():
        for key, category in decisions(pr.body).items():
            decided.setdefault(key, category)

    kept: list[Paper] = []
    pending: list[Paper] = []
    for candidate in candidates:
        key = title_key(candidate.title)
        if key not in decided:
            pending.append(candidate)
        elif category := decided[key]:
            kept.append(candidate.model_copy(update={"category": category}))

    save_papers(PAPERS_PATH, load_papers(PAPERS_PATH) + kept)
    save_papers(CANDIDATES_PATH, pending)
    logger.info(
        "published %d, rejected %d, pending %d", len(kept), len(candidates) - len(kept) - len(pending), len(pending)
    )


if __name__ == "__main__":
    main()
