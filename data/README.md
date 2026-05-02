## Data

This folder contains the primary local dataset used by the project.

Default RAG source:
- `raw/GivenWhenThen.json`

The `python main.py ingest` command reads this file by default and builds the
Chroma index in `chroma_db/`.

Legacy datasets are optional and are no longer required for the normal flow.
