from troposphere import ec2, Export, Output, Ref, Sub, Join, GetAtt
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
import troposphere.elasticloadbalancingv2 as elbv2


class Ec2(object):

    block_device_default = [{"DeviceName": "/dev/sda1",
                             "Ebs": {"DeleteOnTermination": "true"}}]

    def create_elastic_ip(self, name):
        eip = ec2.EIP(name, Domain="vpc")

        self.template.add_resource(eip)

        self.template.add_output(Output(
            name,
            Value=Ref(name),
            Description=u"Elastic IP Address for {}".format(name),
            Export=Export(Sub("${AWS::StackName}-" + name))
        ))
        return eip

    def associate_elastic_ip(self, name, elastic_ip, instance_id):
        self.template.add_resource(ec2.EIPAssociation(
            name,
            EIP=elastic_ip,
            InstanceId=instance_id
        ))

    def add_ec2_launch_configuration(self,
                                     name,
                                     security_groups,
                                     keypair,
                                     image_id='ami-14913f63',
                                     instance_type='t2.micro',
                                     metadata=None,
                                     userdata=None):

        launch_config = LaunchConfiguration(
            name,
            ImageId=image_id,
            SecurityGroups=security_groups,
            InstanceType=instance_type,
            KeyName=keypair
        )

        launch_config.BlockDeviceMappings = self.block_device_default
        if metadata:
            launch_config.Metadata = metadata
        if userdata:
            launch_config.UserData = userdata

        self.template.add_resource(launch_config)

    def add_autoscaling_group(self,
                              name,
                              launch_configuration_name,
                              subnets,
                              desired_size=2,
                              min_size=1,
                              max_size=2,
                              health_check_type='EC2',
                              target_group_arns=[]):
        auto_scaling_group = AutoScalingGroup(
            name,
            DesiredCapacity=desired_size,
            Tags=[{'Key': 'Name', 'Value': name, 'PropagateAtLaunch': True}],
            LaunchConfigurationName=Ref(launch_configuration_name),
            MinSize=min_size,
            MaxSize=max_size,
            VPCZoneIdentifier=subnets,
            HealthCheckType=health_check_type,
            HealthCheckGracePeriod=60,
            TargetGroupARNs=target_group_arns,
            UpdatePolicy=UpdatePolicy(
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime='PT1H',
                    MinInstancesInService=min_size,
                    MaxBatchSize='1',
                    WaitOnResourceSignals=True
                )
            )
        )
        self.template.add_resource(auto_scaling_group)

    def add_security_group(self, name, ingress_rules, vpc, description='Description not supplied', egress_rules=[]):
        self.template.add_resource(
            ec2.SecurityGroup(
                name,
                GroupDescription=description,
                SecurityGroupIngress=ingress_rules,
                SecurityGroupEgress=egress_rules,
                VpcId=vpc,
                Tags=[{'Key': 'Name', 'Value': name}]
            ))

        self.template.add_output(Output(
            name,
            Value=Ref(name),
            Description=u"Security group details for {}".format(name),
            Export=Export(Sub("${AWS::StackName}-" + name))
        ))

    def create_ingress_rule(self, from_port, to_port, cidr_or_sg_id, protocol='tcp'):
        security_group_rule = ec2.SecurityGroupRule(
                IpProtocol=protocol,
                FromPort=from_port,
                ToPort=to_port,
            )
        if isinstance(cidr_or_sg_id, str) or isinstance(cidr_or_sg_id, Join):
            security_group_rule.CidrIp = cidr_or_sg_id
        else:
            security_group_rule.SourceSecurityGroupId = cidr_or_sg_id
        return security_group_rule

    def add_security_group_from_dict(self, name, rules, vpc):
        ingress_rules = []
        for port in rules['ingress']['tcp']:
            sg_rules = []
            for idx, cidr in enumerate(rules['ingress']['tcp'][port]):
                if isinstance(cidr, str) or isinstance(cidr, Join):
                    sg_rules.append(self.create_ingress_rule(
                        port,
                        port,
                        cidr))
                elif isinstance(cidr, Ref):
                    self.add_ingress_rule_to_existing_sg(
                        name='{}{}Rule{}'.format(name, port, idx + 1),
                        dest_sg_id=Ref(name),
                        from_port=port,
                        to_port=port,
                        source_sg_id=cidr,
                    )
            ingress_rules += sg_rules
        self.add_security_group(
            name,
            ingress_rules=ingress_rules,
            vpc=vpc,
        )

    def add_ingress_rule_to_existing_sg(self,
                                        name,
                                        from_port,
                                        to_port,
                                        dest_sg_id,
                                        source_sg_id):
        self.template.add_resource(ec2.SecurityGroupIngress(
            name,
            GroupId=dest_sg_id,
            FromPort=from_port,
            ToPort=to_port,
            IpProtocol='tcp',
            SourceSecurityGroupId=source_sg_id
        ))

    def add_ec2(self,
                name,
                subnet,
                security_groups,
                keypair,
                image_id,
                instance_type,
                network_interfaces=False,
                disable_api_termination=False,
                instance_profile='',
                userdata='',
                metadata=False):

        if not network_interfaces:
            network_interface_config = [ec2.NetworkInterfaceProperty(
                    AssociatePublicIpAddress=False,
                    SubnetId=subnet,
                    GroupSet=security_groups,
                    DeviceIndex=0,
            )]
        else:
            network_interface_config = network_interfaces

        instance = ec2.Instance(
            name,
            ImageId=image_id,
            InstanceType=instance_type,
            DisableApiTermination=disable_api_termination,
            IamInstanceProfile=instance_profile,
            KeyName=keypair,
            NetworkInterfaces=network_interface_config,
            UserData=userdata,
            SourceDestCheck=False,
            Tags=[{'Key': 'Name', 'Value': name}]
        )

        if metadata:
            instance.Metadata = metadata

        self.template.add_resource(instance)
        return instance

    def create_network_interface(self, assign_public_ip, subnet, security_groups, device_index=0, private_ip=False):
        network_interface = ec2.NetworkInterfaceProperty(
                    AssociatePublicIpAddress=assign_public_ip,
                    SubnetId=subnet,
                    GroupSet=security_groups,
                    DeviceIndex=device_index,
        )
        if private_ip:
            network_interface.PrivateIpAddress = private_ip
        return network_interface

    def create_elbv2(self, name, subnets, security_groups=[], lb_type="application", scheme="internet-facing", tags={},
                     lb_attributes=False):
        load_balancer = elbv2.LoadBalancer(
            name,
            Subnets=subnets,
            SecurityGroups=security_groups,
            Scheme=scheme,
            Type=lb_type,
            Tags=tags
        )
        if lb_attributes:
            attributes = []
            for attr in lb_attributes:
                attributes.append(elbv2.LoadBalancerAttributes(
                    Key=attr['key'],
                    Value=attr['value']
                )
                )
            load_balancer.LoadBalancerAttributes = attributes

        self.template.add_resource(load_balancer)

        if lb_type == "application":
            lb_abbreviation = "ALB"
        elif lb_type == "network":
            lb_abbreviation = "NLB"

        self.template.add_output(Output(  # Todo Sort out outputs, based on Type.
            name,
            Value=Ref(name),
            Description=lb_abbreviation + u" ARN",
            Export=Export(Sub("${AWS::StackName}-" + name))
        ))

        self.template.add_output(Output(
            name + "DNS",
            Value=GetAtt(name, "DNSName"),
            Description=lb_abbreviation + u" DNS Name.",
            Export=Export(Sub("${AWS::StackName}-" + name + "DNS"))
        ))

    def elbv2_listener(self, name, lb_arn, protocol, port, default_actions, ssl_policy="", cert_arns=[]):
        certificates = []
        for arn in cert_arns:
            certificates.append(elbv2.Certificate(
                CertificateArn=arn
            ))

        listener = elbv2.Listener(
            name,
            LoadBalancerArn=lb_arn,
            Port=port,
            Protocol=protocol,
            Certificates=certificates,
            SslPolicy=ssl_policy,
            DefaultActions=default_actions
        )

        self.template.add_resource(listener)
        return listener

    def elbv2_listener_action(self, target_group_arn, type="forward"):
        action = elbv2.Action(
            TargetGroupArn=target_group_arn,
            Type=type
        )
        return action

    def elbv2_listener_rule(self, name, actions, conditions, listener_arn, priority):
        self.template.add_resource(elbv2.ListenerRule(
            name,
            Actions=actions,
            Conditions=conditions,
            ListenerArn=listener_arn,
            Priority=priority
        ))

    def elbv2_listener_condition(self, field, values):
        return elbv2.Condition(
            Field=field,
            Values=values
        )

    def elbv2_target_group(self, name, protocol, port, vpc_id, health_check_details={}, matcher=None,
                           target_group_attributes=False, targets=[]):

        target_group = elbv2.TargetGroup(
            name,
            Protocol=protocol,
            Port=port,
            VpcId=vpc_id,
            HealthCheckProtocol=health_check_details["health_check_protocol"],
            HealthCheckPort=health_check_details["health_check_port"],
            HealthCheckIntervalSeconds=health_check_details["health_check_interval"],
            HealthyThresholdCount=health_check_details["healthy_threshold"],
            UnhealthyThresholdCount=health_check_details["unhealthy_threshold"],
            Targets=targets
        )

        if health_check_details.get("health_check_path"):
            target_group.HealthCheckPath = health_check_details["health_check_path"]

        if health_check_details.get("health_check_timeout"):
            target_group.HealthCheckTimeoutSeconds = health_check_details["health_check_timeout"]

        if matcher:
            target_group.Matcher = elbv2.Matcher(
                HttpCode=matcher
            )

        if target_group_attributes:
            attributes = []
            for attr in target_group_attributes:
                attributes.append(elbv2.TargetGroupAttribute(
                    Key=attr['key'],
                    Value=attr['value']
                )
                )
            target_group.TargetGroupAttributes = attributes

        self.template.add_resource(target_group)
        self.template.add_output(Output(
            name,
            Value=Ref(name),
            Description="Target Group {} ARN".format(name),
            Export=Export(Sub("${AWS::StackName}-" + name))
        ))

        return target_group

    def elbv2_target(self, target_id, port):

        return elbv2.TargetDescription(
            Id=target_id,
            Port=port
        )

    def elbv2_health_check_info(self, protocol="HTTP", port=80, path="/",
                                interval=30, timeout=5, healthy_threshold=5,
                                unhealthy_threshold=2):

        info = {}
        info["health_check_protocol"] = protocol
        info["health_check_port"] = port
        info["health_check_path"] = path
        info["health_check_interval"] = interval
        info["health_check_timeout"] = timeout
        info["healthy_threshold"] = healthy_threshold
        info["unhealthy_threshold"] = unhealthy_threshold

        return info
