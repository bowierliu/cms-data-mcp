"""Small curated catalog and documented field meanings; never a live CMS search."""

from typing import Any

LANDING_URL = "https://data.cms.gov/provider-data/dataset/mj5m-pzi6"
DICTIONARY_URL = (
    "https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/"
    "physician/DOC_Data_Dictionary.pdf"
)
DATASET_IDS = {"mj5m-pzi6", "synthetic-count-v1"}
FIELDS: dict[str, tuple[str, str, bool]] = {
    "state": ("string", "Practice state. This approved count is fixed to CA.", True),
    "primary_specialty": (
        "string",
        "Normalized pri_spec; primary enrollment specialty only.",
        True,
    ),
    "record_count": (
        "integer",
        "Nonnegative count of enrollment/location records, not distinct people.",
        True,
    ),
    "npi": (
        "string",
        "National Provider Identifier; not a unique enrollment/location row key. "
        "Schema metadata only; real identifier values are never retrieved.",
        False,
    ),
    "pri_spec": (
        "string",
        "Source primary enrollment specialty; normalized as primary_specialty.",
        False,
    ),
    "citytown": ("string", "Source practice city; metadata only, not county membership.", False),
    "zip_code": ("string", "Source ZIP; metadata only, not an exact county mapping.", False),
}


def search_catalog(query: str, limit: int) -> list[dict[str, Any]]:
    terms = {
        "cms",
        "medicare",
        "provider",
        "providers",
        "doctor",
        "doctors",
        "clinician",
        "clinicians",
        "cardiology",
        "cardiologist",
        "cardiologists",
        "specialty",
        "specialties",
        "physician",
        "physicians",
        "synthetic",
        "fixture",
        "mj5m-pzi6",
    }
    if not set(query.lower().split()) & terms:
        return []
    datasets: list[dict[str, Any]] = [
        {
            "dataset_id": "mj5m-pzi6",
            "title": "National Downloadable File",
            "publisher": "Centers for Medicare & Medicaid Services (CMS)",
            "landing_url": LANDING_URL,
            "synthetic": False,
            "supported_view": "california_primary_cardiology_record_count",
            "grain": "enrollment/location records, not distinct clinicians",
        },
        {
            "dataset_id": "synthetic-count-v1",
            "title": "Fictional fixed cardiology count",
            "publisher": "cms-data-mcp synthetic fixture",
            "landing_url": None,
            "synthetic": True,
            "supported_view": "california_primary_cardiology_record_count",
            "grain": "fictional enrollment/location records, not distinct clinicians",
        },
    ]
    return datasets[:limit]
