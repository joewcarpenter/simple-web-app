from modules.EC2 import Ec2
from modules.VPC import Vpc
from troposphere import Ref, Template
import datetime
import boto3
import botocore


class BaseLayer(Ec2, Vpc):
    def __init__(self, **kwargs):
        self.template = Template()
        self.ref_stack_id = Ref('AWS::StackId')
        self.ref_region = Ref('AWS::Region')
        self.ref_stack_name = Ref('AWS::StackName')
        self.args_dict = kwargs

    def generate_stack(self, stack_name, region, parameters=[]):

        template = self.template.to_json()
        client = boto3.client('cloudformation')
        try:
            boto3.setup_default_session(region_name=region)
            client.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                Parameters=parameters,
                EnableTerminationProtection=False
            )
            print("Stack: {} creating...".format(stack_name))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                print("Stack: {} already exists - submitting change set...".format(stack_name))
                change_set_name = 'changeset' + datetime.datetime.now().isoformat().replace(
                    "-", "").replace(".", "").replace(":", "")
                client.create_change_set(
                    ChangeSetName=change_set_name,
                    StackName=stack_name,
                    TemplateBody=template,
                    Capabilities=[
                        'CAPABILITY_IAM',
                    ],
                    Parameters=parameters)

                try:
                    client.get_waiter('change_set_create_complete').wait(ChangeSetName=change_set_name, StackName=stack_name)
                except botocore.exceptions.WaiterError as e:
                    pass

                resp = client.describe_change_set(ChangeSetName=change_set_name, StackName=stack_name)
                if "didn't contain changes" in resp.get('StatusReason', ''):
                    client.delete_change_set(ChangeSetName=change_set_name, StackName=stack_name)
                    return

                client.execute_change_set(
                    ChangeSetName=change_set_name,
                    StackName=stack_name,
                )
            else:
                print('Unexpected error encountered: {}\n\n'.format(e.response))

