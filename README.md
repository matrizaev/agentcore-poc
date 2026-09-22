# AgentCore Customer Support POC

Production-like Customer Support Agent using:

- AgentCore Runtime + Strands
- AgentCore Gateway + MCP
- AgentCore Memory
- AgentCore Identity
- AgentCore Policy + Cedar
- Lambda + DynamoDB
- CloudWatch / OpenTelemetry

## Demonstrated scenarios

- order check
- customer lookup
- refund
- cross-session preference memory
- <= USD 1,000 ALLOW
- > USD 1,000 DENY
- prompt-injection authorization bypass blocked
- idempotent retry after uncertain outcome
- observable timeout / invalid args / 500 / routing / loop cases

See `docs/architecture.md` and `docs/evidence.md`.

## Security

No credentials are committed. Runtime inbound authentication is IAM. Runtime
obtains outbound OAuth credentials via AgentCore Identity. Refund authorization
is enforced at Gateway by Cedar.
