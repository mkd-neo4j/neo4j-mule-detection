# Feature Architecture

This document describes how features are structured in this repository.

## Design Principles

1. **Cypher-First**: The `.cypher` file is the source of truth. Python is a thin wrapper.
2. **Portable Queries**: Every `.cypher` file can be copied and pasted directly into Neo4j Browser or Workspace.
3. **Self-Contained**: Each feature folder is independent with no cross-feature dependencies.
4. **Documented Value**: Every feature explains *why* it exists, not just *what* it does.

## Folder Structure

Each feature lives in its own folder under `src/features/`:

```
src/features/
├── ARCHITECTURE.md          # This file
├── FEATURES.md              # Feature catalog
│
├── community_mule_density/
│   ├── community_mule_density.cypher
│   ├── community_mule_density.py
│   └── README.md
│
├── distance_to_mule/
│   ├── distance_to_mule.cypher
│   ├── distance_to_mule.py
│   └── README.md
│
└── ...
```

## File Conventions

### `<feature_name>.cypher`

The Cypher query that computes the feature. This file should:

- Be runnable standalone in Neo4j Browser
- Use parameters (e.g., `$accountNumber`) for dynamic values
- Include comments explaining the query logic
- Follow the Neo4j Transaction Data Model conventions

**Example:**

```cypher
// Compute distance to nearest confirmed mule account
// Parameters: $accountNumber - the account to evaluate

MATCH (target:Account {accountNumber: $accountNumber})
MATCH (mule:Account:Confirmed)
MATCH path = shortestPath((target)-[:PERFORMS|BENEFITS_TO*..10]-(mule))
RETURN target.accountNumber AS account,
       length(path) AS distanceToMule,
       mule.accountNumber AS nearestMule
ORDER BY distanceToMule ASC
LIMIT 1
```

### `<feature_name>.py`

A Python wrapper that:

1. Loads the `.cypher` file from the same directory
2. Executes it against a Neo4j database
3. Returns the results in a usable format

**Template:**

```python
"""
Feature: <Feature Name>
Description: <Brief description>
"""

from pathlib import Path
from neo4j import GraphDatabase


def load_query() -> str:
    """Load the Cypher query from the .cypher file."""
    cypher_file = Path(__file__).parent / "<feature_name>.cypher"
    return cypher_file.read_text()


def run(driver: GraphDatabase.driver, **params) -> list[dict]:
    """
    Execute the feature query.

    Args:
        driver: Neo4j driver instance
        **params: Query parameters (e.g., accountNumber="ACC123")

    Returns:
        List of result records as dictionaries
    """
    query = load_query()

    with driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]


if __name__ == "__main__":
    # Example usage
    uri = "neo4j://localhost:7687"
    auth = ("neo4j", "password")

    with GraphDatabase.driver(uri, auth=auth) as driver:
        results = run(driver, accountNumber="ACC123")
        for record in results:
            print(record)
```

### `README.md`

Feature-specific documentation that answers:

1. **Why?**: What business problem does this solve?
2. **What?**: What does the feature compute?
3. **How?**: Brief explanation of the algorithm/approach
4. **Output**: What properties/values are returned or stored?
5. **Usage**: Example of how to use the feature

**Template:**

```markdown
# <Feature Name>

## Why

<Explain the business value. Why would a bank care about this feature?>

## What

<Describe what the feature computes in plain language>

## How

<Brief technical explanation of the approach>

## Output

| Property | Type | Description |
|----------|------|-------------|
| ... | ... | ... |

## Usage

### Cypher (Direct)

\`\`\`cypher
// Example query
\`\`\`

### Python

\`\`\`python
from features.community_mule_density import run
results = run(driver, accountNumber="ACC123")
\`\`\`

## Dependencies

- Neo4j GDS (if applicable)
- Required labels/relationships
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Folder name | `snake_case` | `community_mule_density/` |
| Cypher file | `<folder_name>.cypher` | `community_mule_density.cypher` |
| Python file | `<folder_name>.py` | `community_mule_density.py` |
| Query parameters | `$camelCase` | `$accountNumber`, `$minTransactions` |

## Adding a New Feature

1. Create a new folder: `src/features/<feature_name>/`
2. Write the Cypher query in `<feature_name>.cypher`
3. Test the query in Neo4j Browser
4. Create the Python wrapper using the template above
5. Document the feature in `README.md`
6. Add the feature to `FEATURES.md`

## Dependencies

**Required:**
- Python 3.10+
- `neo4j` Python driver

**Optional:**
- Neo4j Graph Data Science library (for GDS-based features)

Install dependencies:

```bash
pip install neo4j
```

## Testing Features

Each feature can be tested independently:

```bash
# Run a single feature
python -m src.features.community_mule_density.community_mule_density

# Or import and use programmatically
from src.features.community_mule_density import community_mule_density
results = community_mule_density.run(driver, accountNumber="ACC123")
```
