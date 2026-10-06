# Unit test boundary

`test_models.py` covers source identity, unknown release evidence, strict counts,
fixed predicates and resources, safe rejection, hashes, and cache provenance.
Unit tests must not open
network connections or depend on an installed editor. Use synthetic payloads
from `tests/fixtures/` and analytical inputs from `data/fixtures/`.

Count payloads are constructed as synthetic values in pytest fixtures, using the
reviewed request shape. No clinician records are used.
