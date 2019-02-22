from troposphere.ec2 import Route, SubnetRouteTableAssociation, Subnet, RouteTable, VPC, InternetGateway,\
    VPCGatewayAttachment, EIP, NatGateway
from troposphere import GetAtt, Ref


class Vpc():

    def add_vpc(self, name):
        self.template.add_resource(VPC(
            name,
            CidrBlock='10.14.0.0/16',
            )
        )

    def add_subnet(self, name, availability_zone, cidr_block, routing_table_name, vpc_name):
        if isinstance(vpc_name, Ref):
            vpc = vpc_name
        else:
            vpc = Ref(vpc_name)

        self.template.add_resource(
            Subnet(
                name,
                AvailabilityZone=availability_zone,
                CidrBlock=cidr_block,
                VpcId=vpc,
        ))

        self.template.add_resource(
            SubnetRouteTableAssociation(
                "SubnetRouteTableAssociation{}".format(name),
                SubnetId=Ref(name),
                RouteTableId=Ref(routing_table_name),
            )
        )

    def add_internet_gateway(self, name, routing_table_name, vpc_name):
        self.template.add_resource(
            InternetGateway(
                name,
            )
        )

        self.template.add_resource(
            VPCGatewayAttachment(
                'AttachGateway',
                VpcId=Ref(vpc_name),
                InternetGatewayId=Ref(name))
        )

        self.template.add_resource(
            Route(
                "{}IGRoute".format(vpc_name),
                DependsOn='AttachGateway',
                GatewayId=Ref(name),
                DestinationCidrBlock='0.0.0.0/0',
                RouteTableId=Ref(routing_table_name),
            )
        )

    def add_nat_gateway(self, name, subnet):
        eip_name = "{}ElasticIP".format(name)

        self.template.add_resource(EIP(
            eip_name,
            Domain="vpc"
        ))

        self.template.add_resource(NatGateway(
            name,
            AllocationId=GetAtt(eip_name, 'AllocationId'),
            SubnetId=subnet
        ))

    def routing_table(self, name, vpc_name):
        self.template.add_resource(
            RouteTable(
                name,
                VpcId=Ref(vpc_name),
            )
        )

    def add_nat_gateway_route(self, name, dest_cidr_block, route_table_id, nat_gateway_id):
        self.template.add_resource(
            Route(
                name,
                DestinationCidrBlock=dest_cidr_block,
                RouteTableId=route_table_id,
                NatGatewayId=nat_gateway_id,
            )
        )
