import webbrowser
from typing import Literal

import render
from catalog import CANDIDATES_PATH, CATEGORY_HEADINGS, PAPERS_PATH, Category, Paper, load_papers, save_papers

CATEGORIES: list[Category] = list(CATEGORY_HEADINGS)
HELP = "[y] keep  [n] reject  [1-7] keep with category  [o] open link  [q] save and quit\n" + "  ".join(
    f"{number}={category}" for number, category in enumerate(CATEGORIES, 1)
)


def decide(paper: Paper, position: int, total: int) -> Paper | None | Literal["quit"]:
    print(f"\n[{position}/{total}] {paper.title}")
    print(f"  {', '.join(paper.authors[:4])}{' et al.' if len(paper.authors) > 4 else ''}")
    print(f"  {paper.venue} {paper.year}  category: {paper.category}  {paper.url}")
    while True:
        answer = input("> ").strip().lower()
        if answer == "y":
            return paper
        if answer == "n":
            return None
        if answer == "q":
            return "quit"
        if answer == "o":
            webbrowser.open(str(paper.url))
        elif answer.isdigit() and 1 <= int(answer) <= len(CATEGORIES):
            return paper.model_copy(update={"category": CATEGORIES[int(answer) - 1]})
        else:
            print(HELP)


def main() -> None:
    papers = load_papers(PAPERS_PATH)
    candidates = load_papers(CANDIDATES_PATH)
    print(HELP)

    kept: list[Paper] = []
    remaining: list[Paper] = []
    for position, candidate in enumerate(candidates, 1):
        decision = decide(candidate, position, len(candidates))
        if decision == "quit":
            remaining = candidates[position - 1 :]
            break
        if decision:
            kept.append(decision)

    save_papers(PAPERS_PATH, papers + kept)
    save_papers(CANDIDATES_PATH, remaining)
    render.main()
    print(f"\nKept {len(kept)}, {len(remaining)} left for later. README re-rendered.")


if __name__ == "__main__":
    main()
