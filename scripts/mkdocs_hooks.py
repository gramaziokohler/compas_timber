"""MkDocs hooks. Wired in via the `hooks:` key in mkdocs.yml."""

import datetime
import os

import yaml

AUTHORS_TOKEN = "%% authors: generated from CITATION.cff"
YEAR_TOKEN = "%% build-year"
DOI_TOKEN = "%% doi"
REPO_TOKEN = "%% repository-code"


def _bibtex_name(author):
    # BibTeX wants "Family, Given"; entity authors (e.g. a lab) carry a single "name" key and get braces
    # so BibTeX takes the name literally.
    if author.get("family-names"):
        return ", ".join(filter(None, (author["family-names"], author.get("given-names"))))
    return "{{{}}}".format(author.get("name", ""))


def on_page_markdown(markdown, page, config, files):
    """Fills the BibTeX entry in docs/citing.md at build time: authors, DOI and repository URL from CITATION.cff, the year from the clock."""
    if not any(token in markdown for token in (AUTHORS_TOKEN, YEAR_TOKEN, DOI_TOKEN, REPO_TOKEN)):
        return markdown

    root = os.path.dirname(os.path.abspath(config.config_file_path))
    with open(os.path.join(root, "CITATION.cff"), encoding="utf-8") as file:
        cff = yaml.safe_load(file)

    markdown = markdown.replace(YEAR_TOKEN, str(datetime.date.today().year))
    markdown = markdown.replace(DOI_TOKEN, str(cff["doi"]))
    markdown = markdown.replace(REPO_TOKEN, cff["repository-code"])

    lines = []
    for line in markdown.splitlines(keepends=True):
        if line.strip() == AUTHORS_TOKEN:
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(" and\n".join(indent + _bibtex_name(author) for author in cff["authors"]) + "\n")
        else:
            lines.append(line)
    return "".join(lines)
