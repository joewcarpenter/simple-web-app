from troposphere import Ref, cloudformation, Base64, Join
from base.base_layer import BaseLayer
from metadata.instance_metadata import generate_app_server_metadata, generate_app_server_userdata
import argparse


# Ingress can be tied down to a certain address if needed
default_allowed_ingress = ['0.0.0.0/0']
default_keypair_name = 'simple-webapp-key-pair'
default_stack_name = 'simple-web-app'
default_region = 'eu-west-1'


class SimpleWebApp(BaseLayer):
    def __init__(self, stack_name='joe_testing', region='eu-west-1', allowed_ingress='0.0.0.0/0',
                 keypair_name='simple-webapp-key-pair'):
        super(SimpleWebApp, self).__init__()
        self.vpc_name = 'SystemVPC'
        self.region = region
        self.region_public1 = 'eu-west-1a'
        self.region_public2 = 'eu-west-1b'
        self.region_private = 'eu-west-1b'
        self.private_subnet_nat_gateway = 'NatGateway'
        self.stack_name = stack_name
        self.public_routing_table = 'PublicRouting'
        self.public_subnet1 = 'PublicSubnet1'
        self.public_subnet2 = 'PublicSubnet2'
        self.private_routing_table = 'PrivateRouting'
        self.private_subnet = 'PrivateSubnet'
        self.keypair = keypair_name
        # Cast ingress IP to list if not otherwise
        if isinstance(allowed_ingress, list):
            self.allowed_ingress = allowed_ingress
        elif isinstance(allowed_ingress, str):
            self.allowed_ingress = [allowed_ingress]

        # Security group definitions
        self.sgs = {
            "BastionSG": {
                'ingress': {
                    'tcp': {
                        '22': self.allowed_ingress,
                    }
                },
                'egress': {}
            },
            "LBSG": {
                'ingress': {
                    'tcp': {
                        '80': self.allowed_ingress,
                        '22': [Ref('BastionSG')]
                    }
                },
                'egress': {}
            },
            "AppSG": {
                'ingress': {
                    'tcp': {
                        '80': [Ref('LBSG')],
                        '22': [Ref('BastionSG')]
                    }
                },
                'egress': {}
            }
        }

    def create_network(self):
        """
        Creates a VPC, subnets (2 public, 1 private), route tables and gateways
        """
        self.add_vpc(
            name=self.vpc_name
        )

        self.add_subnet(
            name=self.public_subnet1,
            availability_zone=self.region_public1,
            cidr_block='10.14.1.0/24',
            routing_table_name=self.public_routing_table,
            vpc_name=self.vpc_name
        )

        self.add_subnet(
            name=self.public_subnet2,
            availability_zone=self.region_public2,
            cidr_block='10.14.2.0/24',
            routing_table_name=self.public_routing_table,
            vpc_name=self.vpc_name
        )

        self.add_subnet(
            name=self.private_subnet,
            availability_zone=self.region_private,
            cidr_block='10.14.3.0/24',
            routing_table_name=self.private_routing_table,
            vpc_name=self.vpc_name
        )

        self.add_nat_gateway(
            name='NatGateway',
            subnet=Ref(self.public_subnet1)
        )

        self.add_nat_gateway_route(
            name='PrivateRouteToInternet',
            dest_cidr_block='0.0.0.0/0',
            route_table_id=Ref(self.private_routing_table),
            nat_gateway_id=Ref(self.private_subnet_nat_gateway)
        )

        self.add_internet_gateway(
            name='InternetGateway',
            routing_table_name=self.public_routing_table,
            vpc_name=self.vpc_name
        )

        self.routing_table(
            name=self.public_routing_table,
            vpc_name=self.vpc_name
        )
        self.routing_table(
            name=self.private_routing_table,
            vpc_name=self.vpc_name
        )

    def add_security_groups(self):
        """
        Create all necessary Security Groups
        """
        for sg in self.sgs:
            self.add_security_group_from_dict(
                name=sg,
                rules=self.sgs[sg],
                vpc=Ref(self.vpc_name))

    def add_bastion(self):
        """
        Add a Bastion server to the public subnet and assign an EIP
        """
        network_interface = self.create_network_interface(
            assign_public_ip=True,
            subnet=Ref(self.public_subnet1),
            security_groups=[Ref('BastionSG')],
            private_ip=False
        )

        self.create_elastic_ip(
            name='BastionEIP'
        )

        self.associate_elastic_ip(
            name='BastionEIPAssociation',
            elastic_ip=Ref('BastionEIP'),
            instance_id=Ref('BastionServer')
        )

        self.add_ec2(
            name='BastionServer',
            subnet=Ref(self.public_subnet1),
            security_groups=[Ref('BastionSG')],
            keypair=self.keypair,
            image_id='ami-3548444c',
            instance_type='t2.nano',
            userdata=Base64(Join('', ['#!/bin/bash\nshutdown'])),
            network_interfaces=[network_interface]
        )

    @staticmethod
    def create_server_metadata(metadata):
        return cloudformation.Metadata(
            cloudformation.Init({
                'config': cloudformation.InitConfig(
                    packages=metadata['packages'],
                    sources=metadata['sources'],
                    files=metadata['files'],
                    commands=metadata['commands']
                )
            })
        )

    def add_load_balancer(self):
        """
        Add an ALB, target group and listener
        """
        self.create_elbv2(
            name='SimpleWebAppAlb',
            subnets=[Ref(self.public_subnet1), Ref(self.public_subnet2)],
            security_groups=[Ref('LBSG')],
            lb_type="application",
            scheme="internet-facing",
            tags=[{'Key': 'Name', 'Value': 'SimpleWebAppAlb'}],
            lb_attributes=None
        )

        self.elbv2_target_group(
            name='SimpleWebAppTargetGroup',
            protocol="HTTP",
            port=80,
            vpc_id=Ref(self.vpc_name),
            health_check_details=self.elbv2_health_check_info(),
            matcher="200",
            targets=[])

        actions = [self.elbv2_listener_action(target_group_arn=Ref('SimpleWebAppTargetGroup'))]
        self.elbv2_listener(
            name="SimpleWebAppListener",
            lb_arn=Ref('SimpleWebAppAlb'),
            protocol="HTTP",
            port=80,
            default_actions=actions
        )

    def add_app_asg(self):
        """
        Create an autoscaling group of app servers with associated launch configuration
        """
        self.add_ec2_launch_configuration(
            'AppServerLaunchConfig',
            security_groups=[Ref('AppSG')],
            keypair=self.keypair,
            image_id='ami-3548444c',
            instance_type='t2.nano',
            userdata=generate_app_server_userdata(stack_name=self.stack_name,
                                                  region=self.region),
            metadata=self.create_server_metadata(generate_app_server_metadata())

        )

        self.add_autoscaling_group(
            name='AppServerASG',
            launch_configuration_name='AppServerLaunchConfig',
            subnets=[Ref(self.private_subnet)],
            desired_size=2,
            min_size=1,
            max_size=3,
            health_check_type='EC2',
            target_group_arns=[Ref('SimpleWebAppTargetGroup')],
        )

    def build_stack(self):
        self.create_network()
        self.add_security_groups()
        self.add_bastion()
        self.add_load_balancer()
        self.add_app_asg()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a simple-web-app POC deployment')
    parser.add_argument('--stackname', nargs='?', help='Stack Name (default: \'simple-web-app\')', default=default_stack_name)
    parser.add_argument('--keypair', nargs='?', help='Key Pair Name (default: \'simple-webapp-key-pair\')', default=default_keypair_name)
    parser.add_argument('--region', nargs='?', help='Region to deploy into (default: \'eu-west-1\')', default=default_region)
    parser.add_argument('--allowedingress', nargs='?', help='Ingress IP to Whitelist (default: \'0.0.0.0/0\')',
                        default=default_allowed_ingress)
    args = parser.parse_args()

    stack = SimpleWebApp(
        stack_name=args.stackname,
        region=args.region,
        keypair_name=args.keypair,
        allowed_ingress=args.allowedingress
    )
    stack.build_stack()
    stack.generate_stack(
        stack_name=args.stackname,
        region=args.region
    )
