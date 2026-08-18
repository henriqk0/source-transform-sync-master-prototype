"""Generate the seed fixture files used by ingestion tests.

Mirrors the vendored `backend/data/` column layout (data-model.md section 6)
on a tiny scale. Run: python tests/fixtures/seed/make_fixtures.py
"""

from __future__ import annotations

import json
import os

import pyarrow as pa
import pyarrow.parquet as pq

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

RESEARCHERS = [
    {
        "id": 1,
        "name": "Maria Alice Veiga Ferreira De Souza",
        "identification_id": "LGPD-abc123",
        "birthday": None,
        "cnpq_url": None,
        "google_scholar_url": None,
        "resume": "Professora titular",
        "citation_names": "[]",
        "initiatives": json.dumps(
            [{"id": 10, "name": "Projeto X", "status": "Active"}]
        ),
        "research_groups": "[]",
        "knowledge_areas": "[]",
        "academic_education": "[]",
        "articles": json.dumps(
            [
                {"id": 100, "title": "Publicacao A", "year": 2025, "type": "Journal"},
                {
                    "id": 101,
                    "title": "Publicacao B",
                    "year": 2024,
                    "type": "Conference Event",
                },
            ]
        ),
        "advisorships": "[]",
        "classification": "researcher",
        "classification_confidence": 0.99,
        "classification_note": None,
        "role_evidence": None,
        "was_student": False,
        "was_staff": True,
        "campus": json.dumps({"id": 1, "name": "Vila Velha"}),
    },
    {
        "id": 2,
        "name": "Joao da Silva",
        "identification_id": "LGPD-def456",
        "birthday": None,
        "cnpq_url": None,
        "google_scholar_url": None,
        "resume": None,
        "citation_names": "[]",
        "initiatives": "[]",
        "research_groups": "[]",
        "knowledge_areas": "[]",
        "academic_education": "[]",
        "articles": "[]",
        "advisorships": "[]",
        "classification": "researcher",
        "classification_confidence": 0.9,
        "classification_note": None,
        "role_evidence": None,
        "was_student": False,
        "was_staff": True,
        "campus": json.dumps({"id": 2, "name": "Serra"}),
    },
]

ARTICLES = [
    {
        "id": 100,
        "title": "Publicacao A",
        "doi": "10.1234/a",
        "year": 2025,
        "type": "Journal",
        "journal_conference": "Revista A",
        "volume": "1",
        "pages": "1-10",
        "campus": None,
    },
    {
        "id": 101,
        "title": "Publicacao B",
        "doi": None,
        "year": 2024,
        "type": "Conference Event",
        "journal_conference": None,
        "volume": None,
        "pages": None,
        "campus": None,
    },
]

INITIATIVES = [
    {
        "id": 10,
        "name": "Projeto X",
        "status": "Active",
        "description": None,
        "start_date": "2024-01-01",
        "end_date": None,
        "initiative_type_id": None,
        "initiative_type": None,
        "organization_id": None,
        "organization": None,
        "parent_id": None,
        "team": json.dumps(
            [
                {
                    "id": 10,
                    "person_id": 1,
                    "person_name": "Maria Alice",
                    "role": "Coordinator",
                }
            ]
        ),
        "demandante": None,
        "campus": None,
        "research_group": None,
        "knowledge_areas": "[]",
        "enrichment": None,
        "external_partner": None,
        "external_research_group": None,
    },
    {
        "id": 11,
        "name": "Projeto Fantasma",
        "status": "Active",
        "description": None,
        "start_date": None,
        "end_date": None,
        "initiative_type_id": None,
        "initiative_type": None,
        "organization_id": None,
        "organization": None,
        "parent_id": None,
        "team": json.dumps(
            [
                {
                    "id": 11,
                    "person_id": 999,
                    "person_name": "Fantasminha",
                    "role": "Member",
                }
            ]
        ),
        "demandante": None,
        "campus": None,
        "research_group": None,
        "knowledge_areas": "[]",
        "enrichment": None,
        "external_partner": None,
        "external_research_group": None,
    },
]


def _table(rows: list[dict], columns: list[str]) -> pa.Table:
    arrays = []
    for column in columns:
        values = [row.get(column) for row in rows]
        arrays.append(pa.array(values))
    return pa.table(dict(zip(columns, arrays, strict=False)))


def main() -> None:
    pq.write_table(
        _table(
            RESEARCHERS,
            [
                "id",
                "name",
                "identification_id",
                "birthday",
                "cnpq_url",
                "google_scholar_url",
                "resume",
                "citation_names",
                "initiatives",
                "research_groups",
                "knowledge_areas",
                "academic_education",
                "articles",
                "advisorships",
                "classification",
                "classification_confidence",
                "classification_note",
                "role_evidence",
                "was_student",
                "was_staff",
                "campus",
            ],
        ),
        os.path.join(FIXTURES_DIR, "researchers_only_canonical.parquet"),
    )
    pq.write_table(
        _table(
            ARTICLES,
            [
                "id",
                "title",
                "doi",
                "year",
                "type",
                "journal_conference",
                "volume",
                "pages",
                "campus",
            ],
        ),
        os.path.join(FIXTURES_DIR, "articles_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {"production_id": 100, "researcher_id": 1},
                {"production_id": 101, "researcher_id": 1},
            ],
            ["production_id", "researcher_id"],
        ),
        os.path.join(FIXTURES_DIR, "production_authors_canonical.parquet"),
    )
    pq.write_table(
        _table(
            INITIATIVES,
            [
                "id",
                "name",
                "status",
                "description",
                "start_date",
                "end_date",
                "initiative_type_id",
                "initiative_type",
                "organization_id",
                "organization",
                "parent_id",
                "team",
                "demandante",
                "campus",
                "research_group",
                "knowledge_areas",
                "enrichment",
                "external_partner",
                "external_research_group",
            ],
        ),
        os.path.join(FIXTURES_DIR, "initiatives_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 1,
                    "name": "Vila Velha",
                    "description": None,
                    "short_name": None,
                    "organization_id": 1,
                    "parent_id": None,
                },
                {
                    "id": 2,
                    "name": "Serra",
                    "description": None,
                    "short_name": None,
                    "organization_id": 1,
                    "parent_id": None,
                },
            ],
            ["id", "name", "description", "short_name", "organization_id", "parent_id"],
        ),
        os.path.join(FIXTURES_DIR, "campuses_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 1,
                    "name": "Instituto Federal do Espirito Santo",
                    "description": None,
                    "short_name": "IFES",
                },
            ],
            ["id", "name", "description", "short_name"],
        ),
        os.path.join(FIXTURES_DIR, "organizations_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [{"id": 1, "name": "Engenharia Eletrica"}],
            ["id", "name"],
        ),
        os.path.join(FIXTURES_DIR, "knowledge_areas_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 1,
                    "name": "Grupo de Pesquisa",
                    "description": None,
                    "short_name": "GP",
                    "organization_id": 1,
                    "campus_id": 1,
                    "cnpq_url": None,
                    "site": None,
                }
            ],
            [
                "id",
                "name",
                "description",
                "short_name",
                "organization_id",
                "campus_id",
                "cnpq_url",
                "site",
            ],
        ),
        os.path.join(FIXTURES_DIR, "research_groups_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 200,
                    "title": "Livro",
                    "year": 2023,
                    "production_type_id": 1,
                    "publisher": "Editora",
                    "isbn": None,
                    "edition": None,
                    "book_title": None,
                    "pages": None,
                    "version": None,
                    "platform": None,
                    "link": None,
                }
            ],
            [
                "id",
                "title",
                "year",
                "production_type_id",
                "publisher",
                "isbn",
                "edition",
                "book_title",
                "pages",
                "version",
                "platform",
                "link",
            ],
        ),
        os.path.join(FIXTURES_DIR, "research_productions_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [{"id": 1, "name": "Book"}],
            ["id", "name"],
        ),
        os.path.join(FIXTURES_DIR, "production_types_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 300,
                    "name": "Dissertacao",
                    "status": "Concluded",
                    "description": None,
                    "start_date": None,
                    "end_date": None,
                    "campus": None,
                    "advisorships": None,
                    "team": "[]",
                }
            ],
            [
                "id",
                "name",
                "status",
                "description",
                "start_date",
                "end_date",
                "campus",
                "advisorships",
                "team",
            ],
        ),
        os.path.join(FIXTURES_DIR, "advisorships_canonical.parquet"),
    )
    pq.write_table(
        _table(
            [
                {
                    "id": 400,
                    "name": "Bolsa",
                    "description": "desc",
                    "value": 1000,
                    "campus": None,
                },
            ],
            ["id", "name", "description", "value", "campus"],
        ),
        os.path.join(FIXTURES_DIR, "fellowships_canonical.parquet"),
    )
    with open(os.path.join(FIXTURES_DIR, "_meta.json"), "w") as handle:
        json.dump(
            {"generated_at": "2026-08-18", "source_commit": "test-fixture"}, handle
        )

    print(f"Fixtures written to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
