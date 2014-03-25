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

## Running a bot locally

```
python battleships/util/player.py battleships path/to/your/bot
```

Which will give you a summary of the game, including error data if the bot fails:
```
{'bot_request': '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0',
 'bot_response': 'x',
 'error_message': 'The bot made an illegal move',
 'error_type': 'BOT_MOVE_ILLEGAL',
 'game_seed': 0.8071676709968092,
 'success': False}
```

For a list of available options:
```
python battleships/util/player.py -h
```
