# Counterparty Diversity

## Why

Mule accounts often exhibit a distinctive pattern: **high transaction volume with limited counterparties**. While legitimate accounts build diverse transaction networks over time—paying bills to various merchants, receiving payments from multiple sources—mule accounts typically transact with a small, concentrated set of accounts as they funnel illicit funds through the network.

This feature calculates **counterparty diversity metrics** to identify accounts that:
- Move high volumes through few relationships (potential layering)
- Have concentrated activity with a single counterparty (potential collusion)
- Deviate from normal transactional diversity patterns

**Business value:**
- Identify accounts with suspicious transaction patterns
- Detect layering activity in money laundering
- Flag concentrated relationships for investigation
- Complement network analysis with behavioural signals

## What

Calculate four **diversity metrics** for each account:

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| `uniqueCounterparties` | Count distinct accounts | Number of different accounts transacted with |
| `totalTransactions` | Count all transactions | Total activity volume (in + out) |
| `diversityRatio` | counterparties / transactions | Low ratio = concentrated activity |
| `topCounterpartyShare` | max(cp_count) / transactions | High share = dominated by one counterparty |

**Example interpretations:**
- `diversityRatio = 0.05` → 20 transactions with only 1 counterparty (suspicious)
- `diversityRatio = 0.50` → 20 transactions with 10 counterparties (normal)
- `topCounterpartyShare = 0.80` → 80% of transactions with one account (concentrated)
- `topCounterpartyShare = 0.10` → Transactions spread across many counterparties (normal)

## Architecture

This feature supports **two modes** of operation:

### Option 1: Real-Time On-the-Fly (Recommended)
Calculate diversity metrics at query time for source and target accounts:
- **Fresh data:** Always calculates from current transaction state
- **No batch dependency:** Works immediately without pre-computation
- **Simpler operations:** No need to schedule periodic batch updates
- **Trade-off:** Slightly more expensive per-query, but acceptable for single-account lookups

### Option 2: Batch + Lookup
Pre-compute metrics for all accounts, then lookup at query time:
1. **Batch:** Calculate diversity metrics for all Account/Mule nodes, write to properties
2. **Lookup:** Simple property lookup for account being evaluated

**No GDS required:** Both modes use pure Cypher aggregation.

## Cypher Files

| File | Type | Purpose |
|------|------|---------|
| `3-query-realtime.cypher` | Real-time | Calculate diversity on-the-fly for source + target |
| `1-calculate-diversity.cypher` | Batch | Calculate and write all metrics to nodes |
| `2-query-account.cypher` | Lookup | Lookup pre-computed diversity for an account |

## Output

### Real-Time Query Response (3-query-realtime.cypher)

| Field | Type | Description |
|-------|------|-------------|
| `sourceAccount` | String | Source account number |
| `sourceUniqueCounterparties` | Integer | Source's unique counterparties |
| `sourceTotalTransactions` | Integer | Source's total transactions |
| `sourceDiversityRatio` | Float | Source's diversity ratio |
| `sourceTopCounterpartyShare` | Float | Source's top counterparty share |
| `targetAccount` | String | Target account number |
| `targetUniqueCounterparties` | Integer | Target's unique counterparties |
| `targetTotalTransactions` | Integer | Target's total transactions |
| `targetDiversityRatio` | Float | Target's diversity ratio |
| `targetTopCounterpartyShare` | Float | Target's top counterparty share |

### Properties Written to Nodes (Batch)

| Property | Type | Description |
|----------|------|-------------|
| `uniqueCounterparties` | Integer | Count of distinct accounts transacted with |
| `totalTransactions` | Integer | Total transaction count (in + out) |
| `diversityRatio` | Float | uniqueCounterparties / totalTransactions |
| `topCounterpartyShare` | Float | Fraction of transactions with top counterparty |

## Usage

### Cypher

**Real-time query** (recommended - calculates on-the-fly):
```cypher
:param sourceAccount => 'ACC_MULE_55937'
:param targetAccount => 'ACC_CUST_2155'
:source 3-query-realtime.cypher
```

**Batch processing** (alternative - run periodically):
```cypher
:source 1-calculate-diversity.cypher
```

**Lookup pre-computed** (after batch):
```cypher
:param accountNumber => 'ACC_CUST_835'
:source 2-query-account.cypher
```

**Find suspicious accounts** (after batch):
```cypher
MATCH (a:Account)
WHERE a.diversityRatio < 0.1 AND a.totalTransactions > 50
RETURN a.accountNumber, a.diversityRatio, a.totalTransactions, a.topCounterpartyShare
ORDER BY a.diversityRatio ASC
```

### Python

```python
from neo4j import GraphDatabase
from src.features.counterparty_diversity import counterparty_diversity

uri = "neo4j://localhost:7687"
auth = ("neo4j", "password")

with GraphDatabase.driver(uri, auth=auth) as driver:
    # REAL-TIME: Calculate on-the-fly for transaction evaluation (recommended)
    result = counterparty_diversity.query_realtime(
        driver,
        sourceAccount="ACC_MULE_55937",
        targetAccount="ACC_CUST_2155"
    )

    if result:
        src_ratio = result['sourceDiversityRatio']
        tgt_ratio = result['targetDiversityRatio']

        if src_ratio < 0.1 or tgt_ratio < 0.1:
            print("HIGH RISK: Low diversity detected")
        else:
            print("LOW RISK: Normal diversity")

    # BATCH: Alternative - run periodically to pre-compute
    # results = counterparty_diversity.run_batch(driver)
```

### Command Line

```bash
# Set environment variables
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"

# Real-time mode (default) - calculate on-the-fly
python -m src.features.counterparty_diversity.counterparty_diversity --mode realtime

# Batch mode - update all accounts
python -m src.features.counterparty_diversity.counterparty_diversity --mode batch

# Both modes
python -m src.features.counterparty_diversity.counterparty_diversity --mode both

# Override accounts for real-time query
python -m src.features.counterparty_diversity.counterparty_diversity --source ACC123 --target ACC456
```

**CLI Options:**

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--mode` | `realtime`, `batch`, `both` | `realtime` | Which mode to run |
| `--source` | account number | config value | Source account for real-time |
| `--target` | account number | config value | Target account for real-time |

## Dependencies

**Required:**
- `neo4j` Python driver
- `python-dotenv` (optional, for environment config)

**Required Labels:**
- `Account` — Regular accounts in the system
- `Mule` — Confirmed mule accounts
- `Transaction` — Transaction nodes

**Required Relationships:**
- `PERFORMS` — Account initiates a transaction
- `BENEFITS_TO` — Transaction benefits an account

## Performance Considerations

### Real-Time On-the-Fly Query
- **Speed:** Calculates fresh metrics per query (~10-50ms typical)
- **Scope:** Only processes the two accounts specified
- **Trade-off:** More expensive than property lookup, but always current
- **Best for:** Transaction evaluation where freshness matters

### Batch Processing
- **Scope:** Processes all Account and Mule nodes
- **Frequency:** Run daily or when transaction patterns need updating
- **Duration:** Depends on graph size and transaction volume
- **Best for:** Bulk analysis, reporting, or high-volume systems

### Indexes
```cypher
// Recommended indexes for both modes
CREATE INDEX account_number IF NOT EXISTS FOR (a:Account) ON (a.accountNumber)
CREATE INDEX mule_account_number IF NOT EXISTS FOR (m:Mule) ON (m.accountNumber)
```

## Risk Interpretation

| Diversity Ratio | Transaction Volume | Top CP Share | Risk Level | Action |
|-----------------|-------------------|--------------|------------|--------|
| < 0.05 | > 100 | > 0.5 | Critical | Block, escalate immediately |
| < 0.1 | > 50 | > 0.3 | High | Flag for manual review |
| 0.1 - 0.3 | > 20 | > 0.2 | Medium | Monitor, log for analysis |
| > 0.3 | any | < 0.2 | Low | Allow, standard monitoring |

**Combined signals are stronger:** An account with low diversity AND high top counterparty share AND high volume is more suspicious than any single indicator alone.

## Limitations

- **Merchant/Bank exclusion:** Only Account-to-Account/Mule transactions are counted. Merchant/Bank payments would skew diversity calculations.
- **Self-transactions:** Excluded from calculations (a <> counterparty).

### Batch Mode Only
- **Point-in-time:** Metrics reflect when batch last ran. Re-run after significant new transactions.
- **New accounts:** Accounts created after batch run won't have metrics until next batch.

### Real-Time Mode
- **Query cost:** Slightly more expensive than property lookup, but typically acceptable (~10-50ms).
