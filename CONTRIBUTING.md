# Contribution Guidelines

Suggestions are welcome. Open an issue or a pull request.

- The list covers patent search and understanding that uses images: patent drawings, figure classification, sketch-based and multimodal prior-art search, and vision-language models applied to patents. Text-only patent work is out of scope.
- The README is generated. Add papers to [data/papers.yaml](data/papers.yaml), not to the README, then run `uv run scripts/render.py`.
- One entry per paper, dataset or tool, with `title`, `authors`, `venue`, `year`, `category` (one of the slugs in [scripts/catalog.py](scripts/catalog.py)), `url` and `added`. Add `doi`, `arxiv`, `code`, `data` or `demo` where they exist.
- Run `uv run scripts/verify.py` to check that DOIs match their titles and links resolve.

By contributing, you agree that your contribution is released under [CC0 1.0](LICENSE).
