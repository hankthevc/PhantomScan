# PhantomScan KQL Hunt Pack

This directory contains KQL (Kusto Query Language) queries for Azure Sentinel, Microsoft Defender, and other KQL-based SIEMs.

## Queries

### Hunt 1: Detect pip/npm installations matched against radar feed

Joins process events with PhantomScan's daily feed to find installations of flagged packages.

**Prerequisites**:
1. Export today's feed to CSV:
   ```bash
   python -c "import pandas as pd; pd.read_json('data/feeds/$(date +%Y-%m-%d)/topN.json').to_csv('radar_feed.csv', index=False)"
   ```

2. Upload `radar_feed.csv` to Azure Blob Storage or use inline data

3. Update the `externaldata()` clause with your blob URL

### Hunt 2: Demo with sample data

Uses sample process events from `data/samples/device_procs.csv` for testing.

### Hunt 3: Suspicious install patterns

Detects rapid installation of multiple packages in a short time window (potential compromised account or automated attack).

### Hunt 4: Installations from unusual users

Identifies one-time package installations from accounts that don't normally install packages.

### Hunt 5: Brand prefix patterns

Detects installations of packages with suspicious brand prefixes (openai-, langchain-, etc.).

## Usage

### Azure Sentinel

1. Navigate to **Logs** in your Sentinel workspace
2. Paste the desired query
3. Adjust time ranges as needed
4. Run the query

### Microsoft Defender

1. Go to **Advanced Hunting**
2. Paste the query
3. Modify table names if needed (e.g., `DeviceProcessEvents`)
4. Execute

## Data Sources

These queries use:
- `DeviceProcessEvents` - Process execution logs from MDE
- `externaldata()` - External CSV/JSON data (radar feed)

## Customization

- **Time Range**: Change `ago(7d)` to your desired lookback
- **Package Regex**: Modify extraction patterns for different package managers
- **Risk Threshold**: Filter results by `score >= 0.7` for high-confidence matches

## Sample Device Process CSV

Create `data/samples/device_procs.csv` with columns:
```
Timestamp,DeviceName,AccountName,ProcessCommandLine
2024-01-01T10:00:00Z,WORKSTATION-01,user@example.com,"pip install requests2"
2024-01-01T10:05:00Z,WORKSTATION-02,admin@example.com,"npm install openai-tools"
```

## False Positives

- Legitimate packages with similar names to canonical packages
- Internal packages with brand prefixes
- Development/testing installations

Always verify findings before taking action!

## References

- [KQL Quick Reference](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/)
- [Azure Sentinel Hunting](https://learn.microsoft.com/en-us/azure/sentinel/hunting)
- [MITRE ATT&CK T1195.001 - Supply Chain Compromise](https://attack.mitre.org/techniques/T1195/001/)
