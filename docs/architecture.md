## State ownership

- Runtime session: isolated execution lifetime.
- Actor: stable opaque memory owner.
- Memory session: one logical conversation.
- Namespace: hierarchical long-term-memory grouping.
- AgentCore Memory: conversational state/preferences.
- DynamoDB: authoritative business state.

## Authorization

Gateway Policy/Cedar evaluates the actual MCP tool call. A refund is permitted
only when the authenticated OAuth principal has the refund scope and
`0 < amount <= 1000`.

The LLM/system prompt is not the authorization boundary.

## Reliability

Refunds are keyed by durable `idempotency_key`. Conditional creation prevents
concurrent/retried requests from creating a second logical refund.

## Observability

The Runtime session ID is propagated in OpenTelemetry baggage. CloudWatch
Transaction Search identifies traces/spans; Lambda logs expose backend request
IDs and exceptions.
