permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"BusinessTools___refund_customer",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-1:002040198363:gateway/agentcorepoc-supportgateway-u6umw2srws"
)
when {
  principal.hasTag("scope") &&
  principal.getTag("scope") like "*support-api/refund*" &&
  context.input.amount > 0 &&
  context.input.amount <= 1000
};
