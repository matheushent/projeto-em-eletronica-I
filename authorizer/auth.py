import logging
import boto3

def handler(event, context):
    """
    Utility function to verify authentication and return the appropriated policy.
    """
    print(event)

    apigw = boto3.client('apigateway')

    # doc: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigateway.html#APIGateway.Client.get_api_keys
    keys = list(map(
        lambda item: item.get("value"),
        apigw.get_api_keys(
            limit=500,
            includeValues=True
        ).get("items")
    ))

    key = event["authorizationToken"]

    if key in keys:
        return generate_policy("user", "Allow", event["methodArn"])
    else:
        return generate_policy("user", "Deny", event["methodArn"])

def generate_policy(principal_id, effect, method_arn):
    """
    Utility function to generate a policy document

    Args:
        principal_id (str): request's user
        effect (str): Allow or Deny
        method_arn (str): resource's ARN

    Returns: dict
    """

    if not effect or not method_arn:

        return None

    response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": method_arn
            }]
        }
    }

    return response