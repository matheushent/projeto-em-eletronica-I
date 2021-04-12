from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_secretsmanager as sm,
)


class Project(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # get VPC
        vpc = ec2.Vpc.from_lookup(self, "Vpc", is_default=True)

        vpc.add_gateway_endpoint(
            id="DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )

        # security group
        security_group = ec2.SecurityGroup(
            self, "SecurityGroup",
            vpc=vpc, security_group_name="project-sg"
        )

        # define role for the API
        lambda_role = iam.Role(
            self, "LambdaHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:*"],
            resources=["*"]
        ))
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface",
                    "ec2:AssignPrivateIpAddresses",
                    "ec2:UnassignPrivateIpAddresses"],
                resources=["*"]))

        # define role for the Authorizer
        authorizer_role = iam.Role(
            self, "ProjectAuthRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            role_name="ProjectAuthorizerRole"
        )

        # define role for the Authorizer lambda function
        authorizer_handler_role = iam.Role(
            self, "ProjectAuthHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="ProjectAuthorizerHandlerRole"
        )

        authorizer_handler_role.add_to_policy(iam.PolicyStatement(
            actions=["apigateway:GET"],
            resources=["*"]
        ))

        authorizer_handler_role.add_to_policy(iam.PolicyStatement(
            actions=["logs:CreateLogStream", "logs:CreateLogGroup"],
            resources=[f"arn:aws:logs:*:{kwargs.get('env').account}:log-group:*"]
        ))

        authorizer_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:PutLogEvents"],
                resources=[f"arn:aws:logs:*:{kwargs.get('env').account}:log-group:*:log-stream:*"]))

        # build layer for the API
        # layer = _lambda.LayerVersion(
        #     self, "ProjectLayer",
        #     code=_lambda.Code.from_asset("layer.zip")
        # )

        lambda_handler = _lambda.Function(
            self, 'ProjectHandler',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('src'),
            handler='routes.get_tables_names',
            # layers=[layer], role=lambda_role,
            role=lambda_role, allow_public_subnet=True,
            vpc=vpc, retry_attempts=0,
            security_groups=[security_group],
            tracing=_lambda.Tracing.ACTIVE,
            timeout=core.Duration.seconds(60)
        )

        authorizer_handler = _lambda.Function(
            self, 'ProjectAuthorizerHandler',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('authorizer'),
            handler='auth.handler',
            timeout=core.Duration.seconds(30),
            role=authorizer_handler_role,
            retry_attempts=0
        )

        # enable authorizer to invoke lambda function
        authorizer_role.add_to_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[authorizer_handler.function_arn]
        ))

        # setup authorizer and api
        authorizer = apigw.TokenAuthorizer(
            self, "Authorizer",
            identity_source=apigw.IdentitySource.header('Authorization'),
            handler=authorizer_handler,
            assume_role=authorizer_role,
            authorizer_name="ProjectAuthorizer",
            results_cache_ttl=core.Duration.seconds(0)
        )

        api = apigw.RestApi(
            self, "ProjectRestApi",
            rest_api_name="ProjectRestApi",
            deploy_options=apigw.StageOptions(
                tracing_enabled=True,
                data_trace_enabled=True,
                stage_name="v1"
            )
        )

        dynamodb_resource = api.root.add_resource("dynamodb")

        get_tables_node_integration = apigw.LambdaIntegration(
            lambda_handler)
        dynamodb_resource.add_method(
            "GET", get_tables_node_integration,
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )
