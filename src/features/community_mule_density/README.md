# Community Mule Density

## Why

Mules rarely operate in isolation. They work in **networks**, clusters of accounts that transact with each other to layer and move illicit funds. If an account belongs to a community where 11 out of 20 accounts are confirmed mules, the probability that this account is also a mule is significantly higher than if it belongs to a community with no mules at all.

This feature leverages graph community detection to identify **guilt by association at scale**. Rather than looking at individual relationships, it analyses the entire neighbourhood structure to calculate risk.

**Business value:**
- Identify accounts operating within known mule networks
- Prioritise investigations based on community-level risk
- Detect new mules by their association with confirmed mules
- Understand the structure and density of fraud rings

## What

Calculate the **mule density** for each account's community:

```
mule_density = confirmed_mules_in_community / total_accounts_in_community
```

For example:
- `muleDensity = 0.55` → 55% of accounts in this community are confirmed mules
- `muleDensity = 0.05` → Only 5% are mules (lower risk)
- `muleDensity = 0.00` → No confirmed mules in this community

## Architecture

This feature uses a **batch + real-time** pattern for efficiency:

### Batch Processing (run periodically)
1. Project graph → Create GDS Cypher projection with weighted account-to-account relationships
2. Detect communities → Run weighted Louvain, write `communityId` to nodes
3. Calculate density → Write `muleDensity`, `communitySize`, `muleCount` to nodes
4. Cleanup → Drop GDS projection

### Graph Projection Strategy

The projection uses **Cypher projection** to create virtual weighted relationships between accounts that transact directly with each other:

```
Account A --PERFORMS--> Transaction --BENEFITS_TO--> Account B
Creates: Account A --[weight: totalAmount]--> Account B
```

**Why this approach:**
- **Amount-weighted:** A £1M transaction creates a stronger connection than 100 x 1p transactions
- **Direct relationships:** Only Account-to-Account/Mule transactions (excludes Merchants/Banks which would dominate communities)
- **Virtual:** No relationships persisted to database; exists only in GDS memory

### Real-Time Query (per transaction)
- Simple property lookup for source and target accounts
- No GDS, no aggregation, just read pre-computed values
- Millisecond response time

## Cypher Files

| File | Type | Purpose |
|------|------|---------|
| `1-project-graph.cypher` | Batch | Create GDS Cypher projection (amount-weighted) |
| `2-detect-communities.cypher` | Batch | Run weighted Louvain, write `communityId` to nodes |
| `3-calculate-density.cypher` | Batch | Calculate and write density to nodes |
| `4-query-accounts.cypher` | Real-time | Lookup source + target account densities |
| `5-cleanup.cypher` | Batch | Drop the GDS projection |

## Output

### Properties Written to Nodes (Batch)

| Property | Type | Description |
|----------|------|-------------|
| `communityId` | Integer | Louvain community identifier |
| `communitySize` | Integer | Total accounts in the community |
| `muleCount` | Integer | Confirmed mules in the community |
| `muleDensity` | Float | Ratio of mules (0.0 - 1.0) |

### Query Response (Real-time)

| Field | Type | Description |
|-------|------|-------------|
| `sourceAccount` | String | Source account number |
| `sourceCommunityId` | Integer | Source's community |
| `sourceMuleDensity` | Float | Mule density for source |
| `targetAccount` | String | Target account number |
| `targetCommunityId` | Integer | Target's community |
| `targetMuleDensity` | Float | Mule density for target |

## Usage

### Cypher (Step by Step)

**Batch processing** (run once, or periodically):
```cypher
// Step 1: Project the graph
:source 1-project-graph.cypher

// Step 2: Detect communities and write to nodes
:source 2-detect-communities.cypher

// Step 3: Calculate density and write to nodes
:source 3-calculate-density.cypher

// Step 5: Cleanup (drop projection)
:source 5-cleanup.cypher
```

**Real-time query** (per transaction):
```cypher
:param sourceAccount => 'ACC_CUST_835'
:param targetAccount => 'ACC_CUST_8'
:source 4-query-accounts.cypher
```

### Python

```python
from neo4j import GraphDatabase
from src.features.community_mule_density import community_mule_density

uri = "neo4j://localhost:7687"
auth = ("neo4j", "password")

with GraphDatabase.driver(uri, auth=auth) as driver:
    # BATCH: Run periodically to update densities
    communities = community_mule_density.run_batch(driver)
    print(f"Updated {len(communities)} communities")

    # REAL-TIME: Query per transaction
    result = community_mule_density.run(
        driver,
        sourceAccount="ACC_CUST_835",
        targetAccount="ACC_CUST_8"
    )

    if result:
        threshold = 0.2
        if result['sourceMuleDensity'] > threshold:
            print("Source account in high-risk community")
        if result['targetMuleDensity'] > threshold:
            print("Target account in high-risk community")
```

### Command Line

```bash
# Set environment variables
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"

# Run batch + real-time demo
python -m src.features.community_mule_density.community_mule_density
```

## Dependencies

**Required:**
- `neo4j` Python driver
- Neo4j Graph Data Science (GDS) library

**Required Labels:**
- `Account`: Regular accounts in the system
- `Mule`: Confirmed mule accounts
- `Transaction`: Transaction nodes

**Required Relationships:**
- `PERFORMS`: Account initiates a transaction
- `BENEFITS_TO`: Transaction benefits an account

## Performance Considerations

### Batch Processing
- **Memory:** GDS projections consume heap memory. Cleanup after use.
- **Frequency:** Run daily or when new mules are confirmed
- **Duration:** Depends on graph size; Louvain is O(n log n)

### Real-Time Queries
- **Speed:** Property lookups are O(1) with indexes
- **No GDS:** Batch pre-computes everything; queries just read
- **Indexes:** Create index on `accountNumber` for fast lookups

```cypher
// Recommended indexes
CREATE INDEX account_number IF NOT EXISTS FOR (a:Account) ON (a.accountNumber)
CREATE INDEX mule_account_number IF NOT EXISTS FOR (m:Mule) ON (m.accountNumber)
```

## Risk Interpretation

| Density | Risk Level | Action |
|---------|------------|--------|
| > 0.5 | Critical | Block transaction, escalate immediately |
| 0.2 - 0.5 | High | Flag for manual review |
| 0.05 - 0.2 | Medium | Monitor, log for pattern analysis |
| < 0.05 | Low | Allow, standard monitoring |
| 0.0 | Unknown | No mules in community (may still need other checks) |

## Limitations

- **Point-in-time:** Community structure reflects when batch last ran. Re-run after new mules are confirmed.
- **New accounts:** Accounts added after batch run won't have density until next batch.
- **Community drift:** Communities may change as new transactions occur; recompute periodically.
