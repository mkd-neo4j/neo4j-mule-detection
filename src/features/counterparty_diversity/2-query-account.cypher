// Counterparty Diversity - Step 2: Query Account
// ===============================================
// Fast property lookup for transaction evaluation.
//
// Parameters:
//   $accountNumber - The account to evaluate
//
// Prerequisites:
//   - Run 1-calculate-diversity.cypher first (batch processing)
//
// Returns:
//   accountNumber         - The queried account
//   uniqueCounterparties  - Count of unique counterparties
//   totalTransactions     - Total transaction count
//   diversityRatio        - uniqueCounterparties / totalTransactions
//   topCounterpartyShare  - Fraction of transactions with top counterparty
//
// Usage:
//   Low diversityRatio (< 0.1) with high totalTransactions (> 50) = suspicious
//   High topCounterpartyShare (> 0.5) = concentrated activity

MATCH (a)
WHERE (a:Account OR a:Mule) AND a.accountNumber = $accountNumber
RETURN
    a.accountNumber AS accountNumber,
    a.uniqueCounterparties AS uniqueCounterparties,
    a.totalTransactions AS totalTransactions,
    a.diversityRatio AS diversityRatio,
    a.topCounterpartyShare AS topCounterpartyShare
