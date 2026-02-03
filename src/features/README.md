# Feature Catalog

This document lists all planned and implemented features for mule account detection.

## Status Legend

| Status | Meaning |
|--------|---------|
| Planned | Feature designed but not yet implemented |
| In Progress | Currently being developed |
| Complete | Implemented and tested |

---

## Feature Summary

| # | Feature | Category | GDS Required | Status |
|---|---------|----------|--------------|--------|
| 1 | [Community Mule Density](#1-community-mule-density) | Network | Yes (Louvain) | Complete |
| 2 | [Distance to Known Mule](#2-distance-to-known-mule) | Proximity | No | Complete |
| 3 | [Counterparty Diversity](#3-counterparty-diversity) | Network | No | Complete |
| 4 | [Shared Identity Markers](#4-shared-identity-markers) | Identity | No | Planned |
| 5 | [PageRank Centrality](#5-pagerank-centrality) | Network | Yes (PageRank) | Planned |

---

## Feature Details

### 1. Community Mule Density

**Category:** Network Analysis
**GDS Required:** Yes (Louvain)
**Folder:** `community_mule_density/`

#### Why

Mules often operate in networks. If an account belongs to a community where 11 out of 20 accounts are confirmed mules, the probability that this account is also a mule is significantly higher than if it belongs to a community of 1 million accounts with only 1 mule.

#### What

1. Run Louvain community detection on the transaction graph
2. For each community, calculate: `mule_density = confirmed_mules / total_accounts`
3. Store the `communityId` and `muleDensity` on each `Account` node

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `communityId` | Integer | Louvain community identifier |
| `muleDensity` | Float | Ratio of mules in the community (0.0 - 1.0) |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.muleDensity > 0.1
RETURN a.accountNumber, a.muleDensity
```

---

### 2. Distance to Known Mule

**Category:** Proximity Analysis
**GDS Required:** No
**Folder:** `distance_to_mule/`

#### Why

An account that is 1 hop away from a confirmed mule is far more suspicious than one that is 10 hops away. This feature quantifies "guilt by association" in the transaction network.

#### What

Calculate the shortest path (in transaction hops) from each account to the nearest confirmed mule account.

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `distanceToMule` | Integer | Number of hops to nearest confirmed mule (null if no path) |
| `nearestMuleId` | String | Account number of the nearest mule |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.distanceToMule <= 2
RETURN a.accountNumber, a.distanceToMule, a.nearestMuleId
```

---

### 3. Counterparty Diversity

**Category:** Network Analysis
**GDS Required:** No
**Folder:** `counterparty_diversity/`

#### Why

Mule accounts often transact with a limited set of counterparties (the fraud network) while moving high volumes. Legitimate accounts typically have diverse counterparty relationships. Low diversity + high volume = potential layering.

#### What

Count unique counterparties (both sending and receiving) and calculate the concentration ratio.

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `uniqueCounterparties` | Integer | Count of unique accounts transacted with |
| `totalTransactions` | Integer | Total transaction count |
| `diversityRatio` | Float | Counterparties / Transactions |
| `topCounterpartyShare` | Float | % of transactions with top counterparty |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.diversityRatio < 0.1 AND a.totalTransactions > 50
RETURN a.accountNumber, a.diversityRatio, a.totalTransactions
```

---

### 4. Shared Identity Markers

**Category:** Identity Analysis
**GDS Required:** No
**Folder:** `shared_identity/`

#### Why

Mule networks often share identity elements: the same email across multiple accounts, shared phone numbers, common devices, or overlapping IP addresses. These connections reveal synthetic identities and coordinated fraud rings.

#### What

Find accounts that share identity markers with the target account:
- Email addresses
- Phone numbers
- Devices
- IP addresses
- Physical addresses

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `sharedEmailCount` | Integer | Accounts sharing an email |
| `sharedPhoneCount` | Integer | Accounts sharing a phone |
| `sharedDeviceCount` | Integer | Accounts sharing a device |
| `sharedIPCount` | Integer | Accounts sharing an IP |
| `identityRiskScore` | Float | Composite identity sharing risk |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.identityRiskScore > 0.5
RETURN a.accountNumber, a.identityRiskScore, a.sharedEmailCount
```

---

### 5. PageRank Centrality

**Category:** Network Analysis
**GDS Required:** Yes (PageRank)
**Folder:** `pagerank_centrality/`

#### Why

In a transaction network, some accounts act as hubs—central points through which money flows. These hub accounts are often coordinators in money laundering operations. PageRank identifies accounts with disproportionate influence in the network.

#### What

Run PageRank on the transaction graph and store the centrality score on each account.

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `pageRank` | Float | PageRank centrality score |
| `pageRankPercentile` | Float | Percentile rank (0.99 = top 1%) |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.pageRankPercentile > 0.95
RETURN a.accountNumber, a.pageRank, a.pageRankPercentile
```

---

## Composite Risk Score

After implementing individual features, a composite risk score can be calculated:

```cypher
MATCH (a:Account {accountNumber: $target})
RETURN a.accountNumber,
       (a.muleDensity * 0.25 +
        CASE WHEN a.distanceToMule <= 2 THEN 0.25 ELSE 0 END +
        CASE WHEN a.diversityRatio < 0.1 THEN 0.15 ELSE 0 END +
        a.identityRiskScore * 0.2 +
        CASE WHEN a.pageRankPercentile > 0.95 THEN 0.15 ELSE 0 END
       ) AS compositeRiskScore
```

---

## Implementation Priority

**Phase 1 - Foundation (Complete):**
1. Community Mule Density (Louvain community detection)
2. Distance to Known Mule (shortest path traversal)

**Phase 2 - Network & Identity:**
3. Counterparty Diversity (relationship counting)
4. Shared Identity Markers (entity resolution through shared PII)
5. PageRank Centrality (graph centrality algorithm)
