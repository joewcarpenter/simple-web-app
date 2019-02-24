from troposphere import Output, Ref, GetAtt, If, Not, Equals
from troposphere.rds import DBInstance


class Rds(object):
    def add_rds_mysql_instance(self, resource_name, db_name=False, instance_id=False,
                               mysql_version='5.6', security_groups=[], parameter_group=False, subnet_group='',
                               master_username='', master_password='', multi_az='false', instance_type='db.t2.small',
                               allocated_storage='10', storage_type='standard', snapshot=False,
                               maintenance_window=False, backup_window=False):
        """
        Adds an RDS MYSQL instance. The instance can either be brand new, or created from a snapshot.

        :param resource_name: Name of parameter group resource in CloudFormation
        :param db_name: The name of the MySQL Database RDS instance
        :param instance_id: The instance identifier for the MySQL database (optional)
        :param mysql_version: The version of MySQL to use for the instance
        :param security_groups: An array of security group ids to assign to the instance
        :param parameter_group: The instance's parameter group (optional - RDS default will be used if not specified)
        :param subnet_group: The instance's subnet group
        :param master_username: The master user name for the instance (ignored if creating from snapshot)
        :param master_password: The master password for the intance (ignored if creating from snapshot)
        :param multi_az: True if the instance should be multi-AZ, otherwise False
        :param instance_type: The instance type of the "hardware" running MySQL, e.g. 'db.t2.small'
        :param allocated_storage: The amount of storage allocated to the instance in GB
        :param storage_type: The type of storage (defaults to standard, can also be gp2 - see the RDS documentation)
        :param snapshot: The URN to a snapshot if this instance is being created from a snapshot.
        :param maintenance_window: The maintenance window (e.g. 'mon:03:00-mon:05:00' - See RDS documentation for syntax)
        :param backup_window: The backup window (e.g. '02:30-03:00' - See RDS documentation for syntax)
        """
        instance = DBInstance(resource_name,
                              DBName=db_name,
                              VPCSecurityGroups=security_groups,
                              DBSubnetGroupName=subnet_group,
                              Engine='MySQL',
                              EngineVersion=mysql_version,
                              MasterUsername=master_username,
                              MasterUserPassword=master_password,
                              MultiAZ=multi_az,
                              DBInstanceClass=instance_type,
                              StorageType=storage_type,
                              AllocatedStorage=allocated_storage,
                              Tags=self.resource_tags(resource_name))
        if snapshot:
            has_snapshot = '{}HasSnapshot'.format(resource_name)
            self.template.add_condition(has_snapshot, Not(Equals(snapshot, '')))

            instance.DBSnapshotIdentifier = snapshot
            instance.DBName = If(has_snapshot, Ref('AWS::NoValue'), db_name)
            instance.MasterUsername = If(has_snapshot, Ref('AWS::NoValue'), master_username)
            instance.MasterUserPassword = If(has_snapshot, Ref('AWS::NoValue'), master_password)

        if instance_id:
            instance.DBInstanceIdentifier = instance_id
        if parameter_group:
            instance.DBParameterGroupName = parameter_group
        if maintenance_window:
            instance.PreferredMaintenanceWindow = maintenance_window
        if backup_window:
            instance.PreferredBackupWindow = backup_window

        self.template.add_resource(instance)
        self.template.add_output(Output(
            resource_name,
            Value=Ref(resource_name),
            Description='{} DB Instance'.format(resource_name)
        ))
        self.template.add_output(Output(
            '{}Host'.format(resource_name),
            Value=GetAtt(resource_name, 'Endpoint.Address'),
            Description='{} DB Address'.format(resource_name)
        ))
        self.template.add_output(Output(
            '{}Port'.format(resource_name),
            Value=GetAtt(resource_name, 'Endpoint.Port'),
            Description='{} DB Port'.format(resource_name)
        ))
        self.template.add_output(Output(
            '{}DBName'.format(resource_name),
            Value=db_name,
            Description='{} DB Name'.format(resource_name)
        ))
