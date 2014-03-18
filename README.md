# Battleships

## Installation

The installation process involves checking out the source code from GitHub, which means you'll need an SSH key approved to access this repository in `/root/.ssh`.

Then run this (which takes a few minutes):
```
curl "http://ec2-54-251-28-177.ap-southeast-1.compute.amazonaws.com/static/bash/install.sh" | sudo bash
```

Try it out:
```
http://battleships.local?verify_token=25848a988e544e88986b46324887f675
```

Restart the application:
```
sudo restart battleships
```

Monitor the log:
```
sudo tail -f /var/log/upstart/battleships.log
```
