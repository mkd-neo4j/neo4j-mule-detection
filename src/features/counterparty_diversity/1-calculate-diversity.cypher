// Counterparty Diversity - Step 1: Calculate Diversity Metrics
// ============================================================
// Calculate counterparty diversity and WRITE to Account/Mule nodes.
//
// Writes:
//   uniqueCounterparties  - Count of distinct accounts transacted with
//   totalTransactions     - Total transactions (incoming + outgoing)
//   diversityRatio        - uniqueCounterparties / totalTransactions
//   topCounterpartyShare  - Fraction of transactions with most frequent counterparty
//
// Notes:
//   - Low diversityRatio + high totalTransactions = suspicious (potential mule)
//   - High topCounterpartyShare = concentrated activity with single counterparty
//   - Considers both incoming and outgoing transactions
//   - Excludes self-transactions (a <> counterparty)
//   - Run periodically as batch process to update metrics

// For each Account/Mule, collect outgoing counterparties
MATCH (a)
WHERE a:Account OR a:Mule

// Outgoing: a sends to counterparty (collect separately to avoid Cartesian product)
OPTIONAL MATCH (a)-[:PERFORMS]->(t_out:Transaction)-[:BENEFITS_TO]->(cp_out)
WHERE (cp_out:Account OR cp_out:Mule) AND cp_out <> a

WITH a,
     collect(DISTINCT t_out) AS outTxs,
     collect(cp_out.accountNumber) AS outCpOccurrences

// Incoming: counterparty sends to a (separate match to avoid Cartesian product)
OPTIONAL MATCH (cp_in)-[:PERFORMS]->(t_in:Transaction)-[:BENEFITS_TO]->(a)
WHERE (cp_in:Account OR cp_in:Mule) AND cp_in <> a

WITH a,
     outTxs,
     outCpOccurrences,
     collect(DISTINCT t_in) AS inTxs,
     collect(cp_in.accountNumber) AS inCpOccurrences

// Calculate total transactions and combine counterparty occurrences
WITH a,
     size(outTxs) + size(inTxs) AS totalTransactions,
     [id IN outCpOccurrences WHERE id IS NOT NULL] +
     [id IN inCpOccurrences WHERE id IS NOT NULL] AS allCpOccurrences

// Calculate unique counterparties (distinct account numbers)
WITH a,
     totalTransactions,
     allCpOccurrences,
     size([i IN range(0, size(allCpOccurrences)-1)
           WHERE i = 0 OR NOT allCpOccurrences[i] IN allCpOccurrences[0..i]]) AS uniqueCounterparties

// Find top counterparty frequency by unwinding and counting
WITH a, totalTransactions, uniqueCounterparties, allCpOccurrences
UNWIND CASE WHEN size(allCpOccurrences) > 0 THEN allCpOccurrences ELSE [null] END AS cpId
WITH a, totalTransactions, uniqueCounterparties, cpId, count(*) AS cpCount

// Aggregate to find max frequency per account
WITH a, totalTransactions, uniqueCounterparties,
     max(CASE WHEN cpId IS NOT NULL THEN cpCount ELSE 0 END) AS maxCpCount

// Calculate ratios and write
WITH a,
     uniqueCounterparties,
     totalTransactions,
     CASE WHEN totalTransactions > 0
          THEN round(toFloat(uniqueCounterparties) / totalTransactions, 4)
          ELSE 0.0
     END AS diversityRatio,
     CASE WHEN totalTransactions > 0
          THEN round(toFloat(maxCpCount) / totalTransactions, 4)
          ELSE 0.0
     END AS topCounterpartyShare

// Write properties to node
SET a.uniqueCounterparties = uniqueCounterparties,
    a.totalTransactions = totalTransactions,
    a.diversityRatio = diversityRatio,
    a.topCounterpartyShare = topCounterpartyShare

RETURN a.accountNumber AS accountNumber,
       uniqueCounterparties,
       totalTransactions,
       diversityRatio,
       topCounterpartyShare
ORDER BY diversityRatio ASC, totalTransactions DESC
