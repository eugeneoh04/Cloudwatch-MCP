# CloudWatch Log Analyst — Agentic LLM + MCP + AWS

An end-to-end agentic system where an LLM autonomously authenticates with AWS, queries CloudWatch Logs, and produces structured root-cause analysis — all triggered by a single natural language prompt in Cursor.

---

## What this project demonstrates

- **MCP (Model Context Protocol)** — building a custom tool server that exposes AWS APIs to an LLM
- **Agentic tool use** — the LLM decides which tools to call, writes its own CloudWatch Insights queries, and reasons over real log data without human guidance
- **AWS IAM + boto3** — least-privilege IAM setup, programmatic authentication, and CloudWatch Logs Insights queries via the AWS SDK
- **Practical MLOps intuition** — log analysis and error diagnosis are core MLE responsibilities; this automates the investigative loop

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Developer machine                                          │
│                                                             │
│   Cursor IDE  ──── tool calls ────►  MCP Server (Python)    │
│       │                                     │               │
│   Claude LLM  ◄─── log results ────   boto3 / AWS SDK       │
└─────────────────────────────────────────────────────────────┘
                                             │
                              ┌──────────────▼───────────────┐
                              │  AWS                         │
                              │                              │
                              │  IAM user                    │
                              │  CloudWatch Logs             │
                              │  Lambda (log generator)      │
                              └──────────────────────────────┘
```

**Flow:** You type a prompt in Cursor → Claude sees the available MCP tools → it calls `list_log_groups` to orient itself → constructs and calls `query_logs` with a CloudWatch Insights query it writes itself → your MCP server authenticates with AWS and fetches real log data → Claude reads the results and returns a structured diagnosis.

---

## Demo

### Prompt
```
Check my CloudWatch logs for the last 5 hours. List all the log groups
you can see, then query the Lambda log group for any errors and tell
me what went wrong and why.
```

### Claude's response (condensed)
```
Log groups found:
  - /aws/lambda/mcp-log-generator

Errors in the last 5 hours — two patterns:

1. NullPointerException (field=customer_email)
   Scenarios: fetch_inventory, processing_order, user_login
   Cause: customer_email is null or missing in some user records.
   Fix: Validate at the boundary; use null-safe access on required fields;
        backfill missing emails upstream.

2. TimeoutException (latency_ms=5032, threshold_ms=5000)
   Scenarios: payment_gateway (6×), processing_order (1×), fetch_inventory (1×)
   Cause: downstream dependency consistently 32ms over the 5s cap.
   Fix: Tune client timeouts above realistic p99 latency; add circuit breaker;
        investigate gateway cold starts and DB contention during traffic spikes.
```

### Error breakdown

| Error type | Count | Share |
|------------|------:|------:|
| `TimeoutException` | 8 | 72.7% |
| `NullPointerException` | 3 | 27.3% |

### User impact
Claude identified 6 distinct affected `user_id`s with timestamps, extracted directly from raw CloudWatch log events.

---

## Setup

### Prerequisites
- AWS account (free tier is sufficient)
- Python 3.10+
- Cursor IDE

### 1. Clone the repo

```bash
git clone https://github.com/eugeneoh04/cloudwatch-mcp.git
cd cloudwatch-mcp
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. AWS — create an IAM user

In the AWS console, create a user with programmatic access and attach this inline policy (least-privilege, read-only):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:FilterLogEvents",
      "logs:StartQuery",
      "logs:GetQueryResults",
      "logs:GetLogEvents"
    ],
    "Resource": "*"
  }]
}
```

Save the generated `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

### 4. AWS — deploy the Lambda log generator

1. In the AWS console, create a Lambda function (Python 3.12)
2. Paste the contents of `lambda_function.py` into the inline editor
3. Click **Deploy**, then click **Test** 15–20 times to populate CloudWatch with logs

### 5. Configure environment

```bash
cp .env.example .env
```

Fill in your credentials in `.env`:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=...
```

### 6. Test your AWS connection

```bash
python test_connection.py
# Expected output: /aws/lambda/mcp-log-generator
```

### 7. Wire into Cursor

Create `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/cloudwatch_mcp_server.py"],
      "env": {
        "AWS_ACCESS_KEY_ID": "AKIA...",
        "AWS_SECRET_ACCESS_KEY": "...",
        "AWS_DEFAULT_REGION": "..."
      }
    }
  }
}
```

> Use absolute paths — Cursor does not expand `~`.

Open Cursor → Settings → MCP. A green dot next to `cloudwatch` means the server is connected.

---

## Tools exposed via MCP

| Tool | Description | Arguments |
|------|-------------|-----------|
| `list_log_groups` | Lists all CloudWatch log groups in the account | none |
| `query_logs` | Runs a CloudWatch Logs Insights query | `log_group` (required), `query` (required), `hours_back` (optional, default 1) |

---

## Example prompts

```
What MCP tools do you have available?
```
```
Check my CloudWatch logs for the last 2 hours. List all log groups,
then query the Lambda log group for errors and diagnose each one.
```
```
Group the errors by type, show how frequently each one occurs,
and suggest a fix for each.
```
```
Find all log entries where the payment_gateway scenario failed.
What user_ids were affected and when?
```
```
What percentage of invocations succeeded vs failed in the last hour?
Is there any pattern to when errors occur?
```

---

## Project structure

```
cloudwatch-mcp/
├── cloudwatch_mcp_server.py   # MCP server — exposes CloudWatch tools to the LLM
├── lambda_function.py         # Lambda function that generates structured logs
├── test_connection.py         # Quick IAM + boto3 connectivity check
├── requirements.txt
├── .env.example               # Credentials template
└── .gitignore
```

---

## Key design decisions

**Why MCP over a direct API call?**
MCP gives the LLM the ability to decide when and how to query. It writes the CloudWatch Insights query itself based on your natural language prompt. A direct API call is static; MCP is agentic.

**Why least-privilege IAM?**
The MCP server only needs read access to logs. This mirrors production best practices — no write permissions, no admin access.

**Why CloudWatch Logs Insights over FilterLogEvents?**
Insights supports SQL-like aggregations (`stats count() by reason`) that let the LLM produce quantitative breakdowns and trend analysis, not just raw log dumps.

---

## Technologies

`Python` · `AWS Lambda` · `AWS CloudWatch Logs` · `AWS IAM` · `boto3` · `MCP (Model Context Protocol)` · `Claude` · `Cursor`
