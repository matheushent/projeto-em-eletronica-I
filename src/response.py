"""Core module for HTTP response operations"""

import json

def build_response(code, body=None):
    """
    Utility function to build HTTP responses

    Args:
        code (int): Status code of the response
        body (dict): Body of the response
    """

    return {
        "statusCode": code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    }