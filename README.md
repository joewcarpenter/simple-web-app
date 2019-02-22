# Simple Web App 

This is a working POC to provision a simple web application in AWS, using Cloudformation via troposphere. 

The web-app itself is a simple Python application (using Flask) serving static content over http, deployed into an autoscaling group behind an ALB. Access to servers is available via a Bastion instance, which is powered down after creation.

By default, :80 to the ALB and :22 to the Bastion are exposed over the internet (hence the Bastion is powered down), which can be overridden on l.7 of driver.py

#### Assumptions

- Valid AWS account, credentials etc.
- Pre-existing key pair with name: _simple-webapp-key-pair_
- No existing CFN stack with the name: simple-webapp-stack (because any change sets are automatically executed)
- User has access to the CFN console to retrieve the DNS for the ALB (stack output - key:SimpleWebAppAlbDNS)

#### Deployment

`python driver.py`
-> This will create the infrastructure, configure the application and start it up - nothing else is required.


#### #TODO

- Better dynamic autoscaling based on eg. CPU
- Provide more friendly DNS
- Use SSL! Generate proper certs etc.
- Automatically provision the key pair
- Implement secure HA back-end eg. RDS (although this noddy app doesn't need it...!)
- Comments in the code + better documentation generally
- Network diagram in README.md
- General project structure cleanup
- More feedback to user's CLI - currently the user will have to go to the CFN console for progress and DNS
- ... etc!