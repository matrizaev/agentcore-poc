#!/usr/bin/env bash
set -euo pipefail
: "${ORDERS_TABLE:?}"
: "${CUSTOMERS_TABLE:?}"

aws dynamodb put-item --table-name "$CUSTOMERS_TABLE" --item '{
  "customer_id":{"S":"CUST-001"},
  "name":{"S":"Ada Lovelace"},
  "email":{"S":"ada@example.test"},
  "tier":{"S":"gold"}
}'

aws dynamodb put-item --table-name "$ORDERS_TABLE" --item '{
  "order_id":{"S":"123"},
  "customer_id":{"S":"CUST-001"},
  "status":{"S":"DELAYED"},
  "delay_reason":{"S":"Carrier capacity constraint"},
  "expected_delivery":{"S":"2026-09-25"},
  "currency":{"S":"USD"},
  "total_amount":{"N":"1200"},
  "refunded_amount":{"N":"0"}
}'

aws dynamodb put-item --table-name "$ORDERS_TABLE" --item '{
  "order_id":{"S":"ORDER-TIMEOUT"},
  "customer_id":{"S":"CUST-001"},
  "status":{"S":"PROCESSING"},
  "currency":{"S":"USD"},
  "total_amount":{"N":"100"},
  "refunded_amount":{"N":"0"}
}'

aws dynamodb put-item --table-name "$ORDERS_TABLE" --item '{
  "order_id":{"S":"ORDER-LOOP"},
  "customer_id":{"S":"CUST-001"},
  "status":{"S":"PENDING"},
  "currency":{"S":"USD"},
  "total_amount":{"N":"100"},
  "refunded_amount":{"N":"0"}
}'
