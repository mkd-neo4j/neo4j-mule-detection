# Distance to Known Mule

## Why

An account that is **1 hop away** from a confirmed mule is far more suspicious than one that is **10 hops away**.

This feature quantifies "guilt by association" in the transaction network. When evaluating whether to allow a transaction from Account A to Account B, knowing that B is directly connected to a confirmed mule account is critical risk information.

**Business value:**
- Immediate risk signal during real-time transaction evaluation
- Prioritise accounts for investigation based on proximity to known bad actors
- Identify accounts that may be "one step removed" from fraud networks

## What

Calculate the **shortest path** (in transaction hops) from a target account to the nearest confirmed mule account.

For example:
- `distanceToMule = 1` → The account directly transacted with a mule
- `distanceToMule = 2` → The account transacted with someone who transacted with a mule
- `distanceToMule = null` → No connection to any mule within 10 hops

## How

Uses Neo4j's `shortestPath()` function to find the minimum number of hops between the target account and any account with the `:Confirmed` label (confirmed mule).

The path traverses through the transaction network via:
- `(:Account)-[:PERFORMS]->(:Transaction)` — account initiates transaction
- `(:Transaction)-[:BENEFITS_TO]->(:Account)` — transaction benefits recipient

**Key constraints:**
- Maximum depth of 10 hops (configurable) to prevent expensive queries
- Considers both directions (money in and money out)
- Returns only the single shortest path

## Output

| Property | Type | Description |
|----------|------|-------------|
| `account` | String | The target account number |
| `distanceToMule` | Integer | Number of hops to nearest mule (null if no path exists) |
| `nearestMule` | String | Account number of the nearest confirmed mule |
| `pathNodes` | List | Ordered list of node identifiers in the path (for debugging) |

## Usage

### Cypher (Direct)

```cypher
// Single account lookup
:param accountNumber => 'ACC123'

MATCH (target:Account {accountNumber: $accountNumber})
MATCH (mule:Account:Confirmed)
WHERE target <> mule
MATCH path = shortestPath((target)-[:PERFORMS|BENEFITS_TO*..10]-(mule))
WITH target, mule, path, length(path) AS distance
ORDER BY distance ASC
LIMIT 1
RETURN target.accountNumber AS account,
       distance AS distanceToMule,
       mule.accountNumber AS nearestMule
```

### Python

```python
from neo4j import GraphDatabase
from src.features.distance_to_mule import distance_to_mule

uri = "neo4j://localhost:7687"
auth = ("neo4j", "password")

with GraphDatabase.driver(uri, auth=auth) as driver:
    # Single account
    results = distance_to_mule.run(driver, accountNumber="ACC123")
    if results:
        print(f"Distance: {results[0]['distanceToMule']} hops")

    # Batch processing
    accounts = ["ACC123", "ACC456", "ACC789"]
    batch_results = distance_to_mule.run_batch(driver, accounts)
    for acc, data in batch_results.items():
        print(f"{acc}: {data['distanceToMule']} hops to mule")
```

### Command Line

```bash
# Set environment variables
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export TEST_ACCOUNT="ACC123"

# Run the feature
python -m src.features.distance_to_mule.distance_to_mule
```

## Dependencies

**Required:**
- `neo4j` Python driver
- Neo4j database with Transaction Data Model

**Required Labels:**
- `Account` — All accounts in the system
- `Confirmed` — Additional label on accounts confirmed as mules

**Required Relationships:**
- `PERFORMS` — Account initiates a transaction
- `BENEFITS_TO` — Transaction benefits an account

## Performance Considerations

- **Index required:** Create an index on `Account.accountNumber` for fast lookups
- **Max depth:** The 10-hop limit prevents runaway queries; adjust based on your graph size
- **Batch processing:** For bulk analysis, consider running as a GDS algorithm instead

```cypher
// Recommended index
CREATE INDEX account_number IF NOT EXISTS FOR (a:Account) ON (a.accountNumber)
```

## Risk Interpretation

| Distance | Risk Level | Interpretation |
|----------|------------|----------------|
| 1 | Critical | Direct transaction with confirmed mule |
| 2-3 | High | Close proximity to mule network |
| 4-6 | Medium | Connected but not immediate |
| 7-10 | Low | Distant connection |
| null | Unknown | No path found (may be isolated or clean) |
