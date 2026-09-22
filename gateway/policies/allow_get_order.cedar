permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"BusinessTools___get_order",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-1:002040198363:gateway/agentcorepoc-supportgateway-u6umw2srws"
)
when {
  principal.hasTag("scope") &&
  principal.getTag("scope") like "*support-api/read*"
};
