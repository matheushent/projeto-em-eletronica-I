#!/usr/bin/env python3

from aws_cdk import core

from stacks.api import Project


env = core.Environment(
    account = '221966004825',
    region = 'sa-east-1'
)

app = core.App()
Project(
    app, Project.__name__, env=env,
    tags = {
        'Application': 'EEL8051',
        'STAGE': 'dev'
    }
)

app.synth()