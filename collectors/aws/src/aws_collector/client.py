"""boto3 Cost Explorer client, scoped to exactly what `spend-lens-collector`
IAM user is allowed to call: `ce:GetCostAndUsage`, `ce:GetCostForecast`,
`ce:GetDimensionValues`. This module never touches S3 or Lambda, and never
calls `sts:GetCallerIdentity` — that action isn't in the IAM user's granted
policy, so this collector doesn't assume it's available.
"""
from __future__ import annotations

import boto3

from spend_lens_common.config import require_env

# Cost Explorer is a global AWS service reachable only via the us-east-1
# endpoint, regardless of which region any other resource lives in.
COST_EXPLORER_REGION = "us-east-1"


def cost_explorer_client():
    return boto3.client(
        "ce",
        region_name=COST_EXPLORER_REGION,
        aws_access_key_id=require_env("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=require_env("AWS_SECRET_ACCESS_KEY"),
    )
