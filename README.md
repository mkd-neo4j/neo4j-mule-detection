# Mule Account Detection

## Why

Banks face an escalating challenge: money mules facilitate fraud, money laundering, and financial crime by moving illicit funds through seemingly legitimate accounts. Traditional rule-based systems catch only a fraction of mule activity because they analyse transactions in isolation, missing the **relationships** that reveal mule networks.

**Graph databases change the game.**

Neo4j enables banks to model accounts, transactions, and identities as a connected network. This reveals patterns invisible to relational databases:

- An account one hop away from a confirmed mule
- A cluster of accounts with unusually high mule density
- Shared identity markers (emails, phones, devices) across suspicious accounts
- Transaction chains that layer funds through intermediaries

This repository provides the building blocks to operationalise these insights.

## What

A collection of **feature generators** for mule detection, each consisting of:

1. **Cypher queries** that compute graph-based features (e.g., community mule density, distance to known mule, transaction velocity)
2. **Python wrappers** that execute these queries against a Neo4j database
3. **Documentation** explaining the "why" behind each feature

These features are designed to be computed and stored in the graph, then queried in **real-time** when evaluating a transaction.

## The Real-Time Use Case

When Account A attempts to send money to Account B, the bank needs answers in milliseconds:

| Question | Feature |
|----------|---------|
| Is B in a high-density mule community? | Community Mule Density |
| How many hops is B from a known mule? | Distance to Known Mule |
| Does B show abnormal transaction velocity? | Transaction Velocity |
| Is B a new account with high activity? | Account Age vs Activity |
| Does B share identity markers with flagged accounts? | Shared Identity Markers |
| Is B a central hub in the transaction network? | PageRank Centrality |

By pre-computing these features and storing them on nodes, the real-time query becomes a simple property lookup rather than an expensive traversal.

## Data Model

This repository aligns to the [Neo4j Transaction Data Model](https://neo4j.com/developer/industry-use-cases/_attachments/transaction-base-model.txt), which includes:

**Core Nodes:**
- `Account` (with labels: `Internal`, `External`, `HighRiskJurisdiction`, `Flagged`, `Confirmed`)
- `Transaction`
- `Customer`

**Key Relationships:**
- `(:Account)-[:PERFORMS]->(:Transaction)-[:BENEFITS_TO]->(:Account)`
- `(:Customer)-[:HAS_ACCOUNT]->(:Account)`
- `(:Customer)-[:HAS_EMAIL|HAS_PHONE|HAS_ADDRESS]->(...)`

## Project Structure

```
mule-account-detection/
├── README.md                     # This file
├── src/
│   └── features/
│       ├── ARCHITECTURE.md       # How features are structured
│       ├── FEATURES.md           # Catalog of available features
│       └── <feature_name>/       # One folder per feature
│           ├── <feature>.cypher  # The Cypher query (portable)
│           ├── <feature>.py      # Python wrapper
│           └── README.md         # Feature documentation
```

## Getting Started

1. Ensure you have a Neo4j database with the Transaction Data Model loaded
2. Install the Python driver: `pip install neo4j`
3. Browse `src/features/FEATURES.md` to see available features
4. Each feature folder contains a standalone `.cypher` file you can run directly in Neo4j Browser or via the Python wrapper

## GDS Algorithms Used

Several features leverage [Neo4j Graph Data Science](https://neo4j.com/docs/graph-data-science/current/):

| Algorithm | Purpose |
|-----------|---------|
| Louvain | Community detection for mule density calculation |
| Shortest Path | Distance to nearest known mule |
| PageRank | Identify central/influential accounts |
| Weakly Connected Components | Find isolated transaction clusters |

## Contributing

Each feature should be self-contained with:
- A `.cypher` file (the source of truth)
- A `.py` wrapper (thin execution layer)
- A `README.md` explaining the business value

See `src/features/ARCHITECTURE.md` for detailed contribution guidelines.
