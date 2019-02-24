# Simple Web App 

This is a working POC to provision a simple web application in AWS, using Cloudformation via troposphere. 

The web-app itself is a simple Python application (using Flask) serving static content over http, deployed into an autoscaling group behind an ALB. Access to servers is available via a Bastion instance, which is powered down after creation.

By default, :80 to the ALB and :22 to the Bastion are exposed over the internet (hence the Bastion is powered down), which can be overridden on l.7 of driver.py

#### Assumptions

- Valid AWS account, credentials etc.
- Pre-existing key pair available to user
- User has access to the CFN console to retrieve the DNS for the ALB (stack output - key:SimpleWebAppAlbDNS)

#### Deployment

```
python driver.py \
--stackname <STACK_NAME> \
--keypair <KEY_PAIR> \
--region <AWS_REGION> \
--allowedingress <MY_IP_ADDRESS>
```
-> This will create the infrastructure, configure the application and start it up - nothing else is required.


#### #TODO

- Better dynamic autoscaling based on eg. CPU
- Provide more friendly DNS
- Use SSL! Generate proper certs etc.
- Automatically provision the key pair
- Implement secure HA back-end eg. RDS (although this noddy app doesn't need it...!)
- Network diagram in README.md
- More feedback to user's CLI - currently the user will have to go to the CFN console for progress and DNS