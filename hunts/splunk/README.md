# PhantomScan Splunk Hunt Pack

This directory contains Splunk SPL (Search Processing Language) queries for detecting suspicious package installations.

## Queries

### Hunt 1: Pip/npm installs vs radar feed

Joins process events with PhantomScan's daily feed to detect installations of flagged packages.

**Prerequisites**:
1. Export today's feed to CSV:
   ```bash
   python -c "import pandas as pd; pd.read_json('data/feeds/$(date +%Y-%m-%d)/topN.json').to_csv('radar_feed.csv', index=False)"
   ```

2. Upload to Splunk as a lookup:
   - Go to **Settings > Lookups > Lookup table files**
   - Click **New Lookup Table File**
   - Upload `radar_feed.csv`
   - Name it `radar_feed.csv`

3. Create a lookup definition:
   - Go to **Settings > Lookups > Lookup definitions**
   - Click **New Lookup Definition**
   - Name: `radar_feed`
   - Type: File-based
   - Lookup file: `radar_feed.csv`

### Hunt 2: Demo with sample data

Uses sample process events for testing the queries.

**Setup**:
1. Create `data/samples/device_procs.csv` with sample data
2. Upload as a lookup named `device_procs.csv`

### Hunt 3: Suspicious install patterns

Detects rapid installation of multiple packages (≥5) in a 5-minute window.

### Hunt 4: Installations from unusual users

Identifies one-time installations that may indicate account compromise.

### Hunt 5: Brand prefix patterns

Detects packages with suspicious brand prefixes (openai-, langchain-, etc.).

### Hunt 6: Packages with "2" suffix

Finds potential typosquats ending in "2" (e.g., requests2, numpy2).

### Hunt 7: Dashboard summary

Creates an overview of installation activity by ecosystem.

## Usage

### Running Queries

1. Open Splunk Web UI
2. Go to **Search & Reporting**
3. Paste the desired query
4. Adjust time range and index names for your environment
5. Click **Search**

### Customization

Edit these fields for your environment:

```spl
(index=endpoint OR sourcetype=process)  # Change to your index/sourcetype
earliest=-7d                             # Adjust time range
CommandLine                              # Change to your field name (e.g., process_command_line)
host                                     # Change to your hostname field
user                                     # Change to your username field
```

## Data Sources

These queries expect:
- **Process execution logs** with command-line arguments
- Common fields: `_time`, `host`, `user`, `CommandLine` (or equivalent)
- Indexes: `endpoint`, `osquery`, `sysmon`, or similar

### Supported Data Sources

- **Sysmon** (Event ID 1)
- **OSQuery** process events
- **Carbon Black** process execution
- **CrowdStrike Falcon** process telemetry
- **Microsoft Defender** process events (via forwarder)

## Sample Data Format

### device_procs.csv

```csv
Timestamp,DeviceName,AccountName,ProcessCommandLine
2024-01-01T10:00:00Z,WORKSTATION-01,alice@example.com,"pip install requests2"
2024-01-01T10:05:00Z,SERVER-DB-01,bob@example.com,"npm install openai-tools"
2024-01-01T10:10:00Z,LAPTOP-DEV-03,charlie@example.com,"pip3 install langchain-sdk"
```

### radar_feed.csv

Export from PhantomScan feed:

```csv
ecosystem,name,version,score,created_at
pypi,requests2,0.0.1,0.85,2024-01-01T09:30:00Z
npm,openai-tools,1.0.0,0.78,2024-01-01T08:15:00Z
```

## Scheduling

### Create a Scheduled Search

1. Run your query
2. Click **Save As > Alert**
3. Configure:
   - **Title**: PhantomScan - Suspicious Package Installations
   - **Schedule**: Run every hour
   - **Trigger**: Number of results > 0
   - **Actions**: Send email, create ticket, etc.

### Alert Actions

Example alert message:

```
PhantomScan detected $result.install_count$ suspicious package installations:

Package: $result.package_name$
Ecosystem: $result.ecosystem$
Risk Score: $result.RiskScore$
Host: $result.host$
User: $result.user$
Time: $result._time$

Review: https://splunk.example.com/...
```

## Dashboard Creation

### Create a Real-Time Dashboard

1. Run Hunt 7 (Dashboard summary)
2. Click **Save As > Dashboard Panel**
3. Add visualizations:
   - **Pie chart**: Installs by ecosystem
   - **Table**: Top 10 installed packages
   - **Timechart**: Installs over time
   - **Single value**: Total installs today

## False Positives

Common false positives:
- Internal packages with similar names
- Legitimate packages during version upgrades (e.g., `boto3` → `boto3-stubs`)
- Development environment package installations

**Mitigation**:
- Whitelist known-good packages
- Filter by high-risk score (≥0.7)
- Cross-reference with change management tickets

## Troubleshooting

### No Results

- Verify index names and sourcetypes
- Check field names (`CommandLine` vs `process.command_line`)
- Ensure time range covers recent activity
- Test with known package installations

### Lookup Not Working

- Verify lookup file uploaded: `| inputlookup radar_feed.csv | head 10`
- Check permissions on lookup table
- Ensure CSV format is correct (no trailing commas)

## References

- [Splunk Search Reference](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference)
- [Lookup Commands](https://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Lookup)
- [Creating Alerts](https://docs.splunk.com/Documentation/Splunk/latest/Alert/Aboutalerts)
- [MITRE ATT&CK T1195.001](https://attack.mitre.org/techniques/T1195/001/)
