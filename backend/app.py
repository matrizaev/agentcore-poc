from __future__ import annotations

import json
import logging
import os
import time
import uuid
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
ORDERS = dynamodb.Table(os.environ["ORDERS_TABLE"])
CUSTOMERS = dynamodb.Table(os.environ["CUSTOMERS_TABLE"])
REFUNDS = dynamodb.Table(os.environ["REFUNDS_TABLE"])


class BusinessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}


def error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def require_non_empty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BusinessError("INVALID_ARGUMENT", f"{name} must be a non-empty string")
    return value.strip()


def to_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json(v) for v in value]
    return value


def get_order(order_id: str) -> dict[str, Any]:
    order_id = require_non_empty(order_id, "order_id")

    # Deterministic observability case: client-side tool timeout.
    if order_id == "ORDER-TIMEOUT":
        time.sleep(8)

    # Deterministic backend failure case.
    if order_id == "ORDER-500":
        raise RuntimeError("Injected backend failure for observability exercise")

    # Deterministic loop case. The agent will be stopped by a Strands turn limit.
    if order_id == "ORDER-LOOP":
        return ok(
            {
                "order_id": order_id,
                "status": "PENDING",
                "retry_after_seconds": 0,
                "message": "Re-check this order until its status becomes final.",
            }
        )

    item = ORDERS.get_item(
        Key={"order_id": order_id},
        ConsistentRead=True,
    ).get("Item")
    if item is None:
        raise BusinessError("NOT_FOUND", f"order {order_id!r} does not exist")
    return ok(to_json(item))


def get_customer(customer_id: str) -> dict[str, Any]:
    customer_id = require_non_empty(customer_id, "customer_id")
    item = CUSTOMERS.get_item(
        Key={"customer_id": customer_id},
        ConsistentRead=True,
    ).get("Item")
    if item is None:
        raise BusinessError("NOT_FOUND", f"customer {customer_id!r} does not exist")

    # Support-safe projection only.
    return ok(
        {
            "customer_id": item["customer_id"],
            "name": item["name"],
            "email": item["email"],
            "tier": item["tier"],
        }
    )


def refund_customer(
    order_id: str,
    customer_id: str,
    amount: int,
    idempotency_key: str,
) -> dict[str, Any]:
    order_id = require_non_empty(order_id, "order_id")
    customer_id = require_non_empty(customer_id, "customer_id")
    idempotency_key = require_non_empty(idempotency_key, "idempotency_key")

    if isinstance(amount, bool) or not isinstance(amount, int):
        raise BusinessError("INVALID_ARGUMENT", "amount must be an integer")
    if amount <= 0:
        raise BusinessError("INVALID_ARGUMENT", "amount must be positive")

    # Defense in depth. Gateway/Cedar remains the real external authorization
    # boundary and must deny this before Lambda for ordinary calls.
    if amount > 1000:
        raise BusinessError("REFUND_LIMIT_EXCEEDED", "refund exceeds USD 1000")

    existing = REFUNDS.get_item(
        Key={"idempotency_key": idempotency_key},
        ConsistentRead=True,
    ).get("Item")
    if existing is not None:
        return ok({**to_json(existing), "replayed": True})

    order = ORDERS.get_item(
        Key={"order_id": order_id},
        ConsistentRead=True,
    ).get("Item")
    if order is None:
        raise BusinessError("NOT_FOUND", f"order {order_id!r} does not exist")
    if order["customer_id"] != customer_id:
        raise BusinessError("CUSTOMER_ORDER_MISMATCH", "order/customer mismatch")

    remaining = int(order["total_amount"]) - int(order.get("refunded_amount", 0))
    if amount > remaining:
        raise BusinessError(
            "AMOUNT_EXCEEDS_REMAINING_BALANCE",
            f"maximum refundable amount is USD {remaining}",
        )

    refund = {
        "idempotency_key": idempotency_key,
        "refund_id": f"rf_{uuid.uuid4().hex}",
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": amount,
        "currency": str(order.get("currency", "USD")),
        "status": "SUCCEEDED",
        "created_at_epoch": int(time.time()),
    }

    try:
        # Durable idempotency boundary.
        REFUNDS.put_item(
            Item=refund,
            ConditionExpression="attribute_not_exists(idempotency_key)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = REFUNDS.get_item(
            Key={"idempotency_key": idempotency_key},
            ConsistentRead=True,
        ).get("Item")
        if existing is None:
            raise
        return ok({**to_json(existing), "replayed": True})

    # Only the invocation that created the refund reaches this mutation.
    ORDERS.update_item(
        Key={"order_id": order_id},
        UpdateExpression=(
            "SET refunded_amount = if_not_exists(refunded_amount, :zero) + :amount"
        ),
        ExpressionAttributeValues={
            ":zero": Decimal(0),
            ":amount": Decimal(amount),
        },
    )

    # Unknown-outcome test: commit succeeded but response is delayed long enough
    # for the MCP caller to time out. Retry must return this same refund.
    if idempotency_key == "operation-timeout-after-commit":
        time.sleep(8)

    return ok({**refund, "replayed": False})


def tool_name(context: Any) -> str:
    client_context = getattr(context, "client_context", None)
    custom = getattr(client_context, "custom", None) if client_context else None
    if not custom or "bedrockAgentCoreToolName" not in custom:
        raise RuntimeError("missing bedrockAgentCoreToolName")
    return custom["bedrockAgentCoreToolName"].split("___", maxsplit=1)[-1]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    tool = tool_name(context)
    request_id = getattr(context, "aws_request_id", None)
    logger.info(
        json.dumps(
            {
                "event": "tool_invocation",
                "tool": tool,
                "request_id": request_id,
                "arguments": event,
            }
        )
    )

    try:
        if tool == "get_order":
            result = get_order(event["order_id"])
        elif tool == "get_customer":
            result = get_customer(event["customer_id"])
        elif tool == "refund_customer":
            result = refund_customer(
                order_id=event["order_id"],
                customer_id=event["customer_id"],
                amount=event["amount"],
                idempotency_key=event["idempotency_key"],
            )
        else:
            raise BusinessError("UNKNOWN_TOOL", f"unsupported tool {tool!r}")

        logger.info(
            json.dumps(
                {
                    "event": "tool_success",
                    "tool": tool,
                    "request_id": request_id,
                }
            )
        )
        return result

    except BusinessError as exc:
        logger.warning(
            json.dumps(
                {
                    "event": "business_error",
                    "tool": tool,
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                }
            )
        )
        return error(exc.code, exc.message)
    except Exception:
        logger.exception(
            json.dumps(
                {
                    "event": "unexpected_error",
                    "tool": tool,
                    "request_id": request_id,
                }
            )
        )
        raise
