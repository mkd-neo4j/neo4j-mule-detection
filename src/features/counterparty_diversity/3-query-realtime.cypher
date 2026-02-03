// Counterparty Diversity - Real-Time Query
// ========================================
// Calculate counterparty diversity on-the-fly for source and target accounts.
// No pre-computation required - calculates fresh from current transaction data.
//
// Parameters:
//   $sourceAccount - Account initiating the transaction
//   $targetAccount - Account receiving the transaction
//
// Returns for each account:
//   accountNumber         - The account identifier
//   uniqueCounterparties  - Count of distinct counterparties
//   totalTransactions     - Total transactions (in + out)
//   diversityRatio        - uniqueCounterparties / totalTransactions
//   topCounterpartyShare  - Fraction of transactions with top counterparty
//
// Usage:
//   Low diversityRatio (< 0.1) with high totalTransactions (> 50) = suspicious
//   High topCounterpartyShare (> 0.5) = concentrated activity

// Calculate diversity for source account
CALL {
    MATCH (a)
    WHERE (a:Account OR a:Mule) AND a.accountNumber = $sourceAccount

    // Outgoing transactions
    OPTIONAL MATCH (a)-[:PERFORMS]->(t_out:Transaction)-[:BENEFITS_TO]->(cp_out)
    WHERE (cp_out:Account OR cp_out:Mule) AND cp_out <> a

    WITH a,
         collect(DISTINCT t_out) AS outTxs,
         collect(cp_out.accountNumber) AS outCpOccurrences

    // Incoming transactions
    OPTIONAL MATCH (cp_in)-[:PERFORMS]->(t_in:Transaction)-[:BENEFITS_TO]->(a)
    WHERE (cp_in:Account OR cp_in:Mule) AND cp_in <> a

    WITH a,
         outTxs,
         outCpOccurrences,
         collect(DISTINCT t_in) AS inTxs,
         collect(cp_in.accountNumber) AS inCpOccurrences

    // Combine and calculate
    WITH a,
         size(outTxs) + size(inTxs) AS totalTransactions,
         [id IN outCpOccurrences WHERE id IS NOT NULL] +
         [id IN inCpOccurrences WHERE id IS NOT NULL] AS allCpOccurrences

    // Unique counterparties
    WITH a,
         totalTransactions,
         allCpOccurrences,
         size([i IN range(0, size(allCpOccurrences)-1)
               WHERE i = 0 OR NOT allCpOccurrences[i] IN allCpOccurrences[0..i]]) AS uniqueCounterparties

    // Top counterparty frequency
    WITH a, totalTransactions, uniqueCounterparties, allCpOccurrences
    UNWIND CASE WHEN size(allCpOccurrences) > 0 THEN allCpOccurrences ELSE [null] END AS cpId
    WITH a, totalTransactions, uniqueCounterparties, cpId, count(*) AS cpCount
    WITH a, totalTransactions, uniqueCounterparties,
         max(CASE WHEN cpId IS NOT NULL THEN cpCount ELSE 0 END) AS maxCpCount

    RETURN
        a.accountNumber AS accountNumber,
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
}
WITH accountNumber AS sourceAccount,
     uniqueCounterparties AS sourceUniqueCounterparties,
     totalTransactions AS sourceTotalTransactions,
     diversityRatio AS sourceDiversityRatio,
     topCounterpartyShare AS sourceTopCounterpartyShare

// Calculate diversity for target account
CALL {
    MATCH (a)
    WHERE (a:Account OR a:Mule) AND a.accountNumber = $targetAccount

    // Outgoing transactions
    OPTIONAL MATCH (a)-[:PERFORMS]->(t_out:Transaction)-[:BENEFITS_TO]->(cp_out)
    WHERE (cp_out:Account OR cp_out:Mule) AND cp_out <> a

    WITH a,
         collect(DISTINCT t_out) AS outTxs,
         collect(cp_out.accountNumber) AS outCpOccurrences

    // Incoming transactions
    OPTIONAL MATCH (cp_in)-[:PERFORMS]->(t_in:Transaction)-[:BENEFITS_TO]->(a)
    WHERE (cp_in:Account OR cp_in:Mule) AND cp_in <> a

    WITH a,
         outTxs,
         outCpOccurrences,
         collect(DISTINCT t_in) AS inTxs,
         collect(cp_in.accountNumber) AS inCpOccurrences

    // Combine and calculate
    WITH a,
         size(outTxs) + size(inTxs) AS totalTransactions,
         [id IN outCpOccurrences WHERE id IS NOT NULL] +
         [id IN inCpOccurrences WHERE id IS NOT NULL] AS allCpOccurrences

    // Unique counterparties
    WITH a,
         totalTransactions,
         allCpOccurrences,
         size([i IN range(0, size(allCpOccurrences)-1)
               WHERE i = 0 OR NOT allCpOccurrences[i] IN allCpOccurrences[0..i]]) AS uniqueCounterparties

    // Top counterparty frequency
    WITH a, totalTransactions, uniqueCounterparties, allCpOccurrences
    UNWIND CASE WHEN size(allCpOccurrences) > 0 THEN allCpOccurrences ELSE [null] END AS cpId
    WITH a, totalTransactions, uniqueCounterparties, cpId, count(*) AS cpCount
    WITH a, totalTransactions, uniqueCounterparties,
         max(CASE WHEN cpId IS NOT NULL THEN cpCount ELSE 0 END) AS maxCpCount

    RETURN
        a.accountNumber AS accountNumber,
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
}

RETURN
    sourceAccount,
    sourceUniqueCounterparties,
    sourceTotalTransactions,
    sourceDiversityRatio,
    sourceTopCounterpartyShare,
    accountNumber AS targetAccount,
    uniqueCounterparties AS targetUniqueCounterparties,
    totalTransactions AS targetTotalTransactions,
    diversityRatio AS targetDiversityRatio,
    topCounterpartyShare AS targetTopCounterpartyShare
