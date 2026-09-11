# Public research record

The report is a bounded product-research synthesis, not a representative survey and not training data. See PUBLIC-SOURCES.md for URLs, retrieval outcomes and snapshot digests.

Full retrieved pages, extracted posts, response headers and discovery dumps remain local and are excluded from Git. Public availability is not a license to redistribute full pages or train a model. The public record publishes source links, factual collection status, hashes and original analysis only.

The collector is reproducible from the repository root:

    python3 -m venv build/filecraft-research-env
    build/filecraft-research-env/bin/python -m pip install -r research/filecraft/requirements.txt
    build/filecraft-research-env/bin/python research/filecraft/collect.py
    build/filecraft-research-env/bin/python research/filecraft/verify.py

Collection is rate-limited and respects robots denials. Future pages and policies may change; verify.py documents the original snapshot counts and will deliberately fail rather than hide a changed collection. Do not treat collection timestamps or issue status as proof that a problem is still unresolved.
