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
| 3 | [Transaction Velocity](#3-transaction-velocity) | Behavioural | No | Planned |
| 4 | [Account Age vs Activity](#4-account-age-vs-activity) | Behavioural | No | Planned |
| 5 | [Counterparty Diversity](#5-counterparty-diversity) | Behavioural | No | Planned |
| 6 | [Round Amount Detection](#6-round-amount-detection) | Transaction | No | Planned |
| 7 | [Time-of-Day Patterns](#7-time-of-day-patterns) | Behavioural | No | Planned |
| 8 | [Geographic Anomalies](#8-geographic-anomalies) | Geographic | No | Planned |
| 9 | [Shared Identity Markers](#9-shared-identity-markers) | Identity | No | Planned |
| 10 | [PageRank Centrality](#10-pagerank-centrality) | Network | Yes (PageRank) | Planned |

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

### 3. Transaction Velocity

**Category:** Behavioural Analysis
**GDS Required:** No
**Folder:** `transaction_velocity/`

#### Why

Mule accounts often show abnormal transaction patterns: sudden spikes in activity, unusual volumes, or consistent high-frequency transfers. Normal accounts have predictable rhythms; mules deviate from these patterns.

#### What

Calculate transaction frequency metrics over multiple time windows:
- Transactions per day (last 7 days)
- Transactions per week (last 4 weeks)
- Transactions per month (last 3 months)
- Velocity change (current week vs. historical average)

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `txPerDay7d` | Float | Average transactions per day (last 7 days) |
| `txPerWeek4w` | Float | Average transactions per week (last 4 weeks) |
| `velocityChange` | Float | Ratio of current to historical velocity |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.velocityChange > 3.0  // 3x normal activity
RETURN a.accountNumber, a.velocityChange
```

---

### 4. Account Age vs Activity

**Category:** Behavioural Analysis
**GDS Required:** No
**Folder:** `account_age_activity/`

#### Why

Mule accounts are often newly opened and quickly become highly active. A legitimate account builds transaction history gradually; a mule account shows disproportionate activity relative to its age.

#### What

Calculate the ratio of transaction volume to account age, normalised against typical accounts.

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `accountAgeDays` | Integer | Days since account was opened |
| `totalTransactions` | Integer | Total transaction count |
| `activityRatio` | Float | Transactions per day since opening |
| `activityPercentile` | Float | Percentile rank compared to all accounts |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.accountAgeDays < 90 AND a.activityPercentile > 0.95
RETURN a.accountNumber, a.accountAgeDays, a.activityPercentile
```

---

### 5. Counterparty Diversity

**Category:** Behavioural Analysis
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

### 6. Round Amount Detection

**Category:** Transaction Pattern
**GDS Required:** No
**Folder:** `round_amount_detection/`

#### Why

Money launderers often transfer round amounts (e.g., £1,000, £5,000, £10,000) because they're moving predetermined sums rather than paying for actual goods/services. A high proportion of round-amount transactions is a red flag.

#### What

Analyse transaction amounts and calculate the percentage that are "round" (divisible by 100, 500, 1000, etc.).

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `roundAmountCount` | Integer | Transactions with round amounts |
| `roundAmountRatio` | Float | % of transactions that are round amounts |
| `avgRoundAmount` | Float | Average value of round transactions |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.roundAmountRatio > 0.5
RETURN a.accountNumber, a.roundAmountRatio
```

---

### 7. Time-of-Day Patterns

**Category:** Behavioural Analysis
**GDS Required:** No
**Folder:** `time_patterns/`

#### Why

Automated money movement often occurs at unusual hours—late night or early morning when legitimate business is minimal. Mule accounts may show transaction patterns that don't align with normal human behaviour.

#### What

Analyse transaction timestamps to identify:
- Distribution across hours of the day
- Weekend vs. weekday patterns
- Clustering of transactions in unusual time windows

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `nightTxRatio` | Float | % of transactions between 00:00-06:00 |
| `weekendTxRatio` | Float | % of transactions on Saturday/Sunday |
| `peakHour` | Integer | Most common transaction hour (0-23) |
| `timePatternScore` | Float | Anomaly score based on timing |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.nightTxRatio > 0.3
RETURN a.accountNumber, a.nightTxRatio, a.peakHour
```

---

### 8. Geographic Anomalies

**Category:** Geographic Analysis
**GDS Required:** No
**Folder:** `geographic_anomalies/`

#### Why

Transactions to high-risk jurisdictions, or patterns where an account's stated location doesn't match transaction geography, indicate potential money laundering or mule activity.

#### What

Compare account jurisdiction against transaction destinations and identify:
- Transactions to high-risk countries
- Mismatches between customer address and transaction locations
- Unusual cross-border patterns

#### Output Properties

| Property | Type | Description |
|----------|------|-------------|
| `highRiskTxCount` | Integer | Transactions to high-risk jurisdictions |
| `highRiskTxRatio` | Float | % of transactions to high-risk areas |
| `crossBorderRatio` | Float | % of transactions that are international |
| `locationMismatch` | Boolean | Customer address doesn't match tx geography |

#### Use at Query Time

```cypher
MATCH (a:Account {accountNumber: $target})
WHERE a.highRiskTxRatio > 0.2 OR a.locationMismatch = true
RETURN a.accountNumber, a.highRiskTxRatio, a.locationMismatch
```

---

### 9. Shared Identity Markers

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

### 10. PageRank Centrality

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
       (a.muleDensity * 0.2 +
        CASE WHEN a.distanceToMule <= 2 THEN 0.3 ELSE 0 END +
        CASE WHEN a.velocityChange > 3 THEN 0.15 ELSE 0 END +
        a.identityRiskScore * 0.2 +
        CASE WHEN a.pageRankPercentile > 0.95 THEN 0.15 ELSE 0 END
       ) AS compositeRiskScore
```

---

## Implementation Priority

**Phase 1 - Foundation:**
1. Community Mule Density (requires Louvain setup)
2. Distance to Known Mule (core proximity metric)

**Phase 2 - Behavioural:**
3. Transaction Velocity
4. Account Age vs Activity
5. Counterparty Diversity

**Phase 3 - Patterns:**
6. Round Amount Detection
7. Time-of-Day Patterns

**Phase 4 - Advanced:**
8. Geographic Anomalies
9. Shared Identity Markers
10. PageRank Centrality
