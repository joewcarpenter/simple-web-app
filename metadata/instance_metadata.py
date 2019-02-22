from troposphere import Base64, Join
import os


def generate_app_server_userdata(stack_name, region):
    return Base64(Join('', ["""#!/bin/bash
/usr/bin/easy_install --script-dir /opt/aws/bin https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
/opt/aws/bin/cfn-init --resource AppServerLaunchConfig --stack """, stack_name, """ --region """, region,
"""
rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum install -y python-pip
pip install flask
systemctl enable simple_web_app
/opt/aws/bin/cfn-signal -e 0 --resource AppServerASG --stack """, stack_name,
" --region ", region,
"""
systemctl start simple_web_app
"""]))


def generate_app_server_metadata():
    return {
            'packages': {},
            'sources': {},
            'files': {
                '/etc/simple_web_app.py': {
                    'content': open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../files/simple_web_app.py'), 'r').read(),
                    'mode': '000644',
                    'owner': 'root',
                    'group': 'root'
                },
                '/etc/simple_web_app.sh': {
                    'content': open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../files/simple_web_app.sh'), 'r').read(),
                    'mode': '000750',
                    'owner': 'root',
                    'group': 'root'
                },
                '/etc/static/index.html': {
                    'content': open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../files/index.html'), 'r').read(),
                    'mode': '000644',
                    'owner': 'root',
                    'group': 'root'
                },
                '/etc/systemd/system/simple_web_app.service': {
                    'content': open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../files/simple_web_app.service'), 'r').read(),
                    'mode': '000644',
                    'owner': 'root',
                    'group': 'root'
                }
            },
            'commands': {}
        }
