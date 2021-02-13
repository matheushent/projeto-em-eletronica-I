import boto3

from response import build_response

def get_tables_names(event, context):

    dynamodb = boto3.client('dynamodb')

    tables = dynamodb.list_tables()

    return build_response(200, {"message": "Succeeded", "tables": tables})