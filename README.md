# Battleships

## Installation

_The installation guide is designed for Ubuntu and has been tested on a fresh install of Ubuntu 12.04._

The installation process involves checking out the source code from GitHub, which means you'll need an SSH key approved to access this repository in `/root/.ssh`.

Then run this (which takes several minutes):
```
curl "http://ec2-54-251-28-177.ap-southeast-1.compute.amazonaws.com/static/bash/install.sh" | sudo bash
```

Try it out:
```
http://battleships.local:8000?verify_token=25848a988e544e88986b46324887f675
```
(The verify token is only required the first time you visit the application)

Restart the application:
```
sudo restart battleships
```

Monitor the log:
```
sudo tail -f /var/log/upstart/battleships.log
```
