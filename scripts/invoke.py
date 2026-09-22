from __future__ import annotations

import argparse
import json
import uuid

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--session-id")
    args = parser.parse_args()

    session_id = args.session_id or f"session-{uuid.uuid4()}"
    client = boto3.client("bedrock-agentcore")
    response = client.invoke_agent_runtime(
        agentRuntimeArn=args.runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(
            {
                "prompt": args.prompt,
                "actor_id": args.actor_id,
            }
        ).encode(),
        qualifier="DEFAULT",
    )

    raw = "".join(chunk.decode("utf-8") for chunk in response.get("response", []))
    try:
        print(json.dumps(json.loads(raw), indent=2))
    except json.JSONDecodeError:
        print(raw)


if __name__ == "__main__":
    main()
