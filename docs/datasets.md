# Sentinel AI Dataset & Benchmarking Architecture

## 1. Datasets Directory Structure
- `datasets/raw/`: Audio recordings and raw transcript logs.
- `datasets/processed/`: Normalized text pairs with speaker tags.
- `datasets/synthetic/`: LLM-generated scam scripts covering 6 primary fraud vectors.
- `datasets/evaluation/`: Golden evaluation benchmark suite with ground-truth risk scores.

## 2. Scam Vectors Covered
1. **OTP & MFA Theft**: Demands for SMS codes under pretexts of security validation.
2. **Bank Impersonation**: Account freeze warnings, suspicious transfer alerts.
3. **Tech Support Scams**: Supposed virus infection requiring Remote Desktop Access (AnyDesk/TeamViewer).
4. **Government & Tax Impersonation**: IRS/Law Enforcement arrest threats unless paid via gift cards.
5. **Investment & Crypto Fraud**: Guaranteed returns, high-pressure crypto deposits.
6. **Romance & Emergency Scams**: Grandchild accident pretexts, urgent bail requests.
