import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client("logs", region_name="ap-northeast-2")
groups = client.describe_log_groups()

print("Connected! Log groups found:")
for g in groups["logGroups"]:
    print(f"  {g['logGroupName']}")
