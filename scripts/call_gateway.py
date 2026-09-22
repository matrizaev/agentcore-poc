from __future__ import annotations

import argparse
import base64
import json
import urllib.parse
import urllib.request


def get_token(
    *,
    region: str,
    domain_prefix: str,
    client_id: str,
    client_secret: str,
) -> str:
    endpoint = f"https://{domain_prefix}.auth.{region}.amazoncognito.com/oauth2/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "scope": "support-api/read support-api/refund",
        }
    ).encode()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.load(response)["access_token"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--gateway-url", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--domain-prefix", required=True)
    p.add_argument("--client-id", required=True)
    p.add_argument("--client-secret", required=True)
    p.add_argument("--tool", required=True)
    p.add_argument("--arguments", required=True)
    args = p.parse_args()

    access_token = get_token(
        region=args.region,
        domain_prefix=args.domain_prefix,
        client_id=args.client_id,
        client_secret=args.client_secret,
    )

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": args.tool,
            "arguments": json.loads(args.arguments),
        },
    }
    req = urllib.request.Request(
        args.gateway_url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode())
        raise


if __name__ == "__main__":
    main()
