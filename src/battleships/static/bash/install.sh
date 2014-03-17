# Install the Battleships project locally for development.

# install MongoDB
# http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | tee /etc/apt/sources.list.d/mongodb.list
apt-get update
apt-get -y install mongodb-10gen

# install redis
apt-get -y install redis-server

# convert bots uploaded from a Windows system
apt-get -y install tofrodos

# required for 'motor' python package
apt-get -y install build-essential python-dev

# install python packages
apt-get -y install python-pip
pip install motor==0.1.2
pip install tornado==3.1.1
pip install redis==2.7.6
pip install pymongo==2.5
pip install PyYAML==3.10

# create bots directory
mkdir -p /var/lib/battleships/bots

# update /etc/hosts (required for Facebook authentication)
HOSTS_ENTRY="127.0.0.1 battleships.local"
grep -q "$HOSTS_ENTRY" /etc/hosts
if [ $? -ne 0 ]
then
  echo "$HOSTS_ENTRY" >> /etc/hosts
fi

# create developer user account in MongoDB with verify token
mongo --eval "new Mongo().getDB('battleships').users.save({'verify_token': '25848a988e544e88986b46324887f675'});"

# checkout source code and configure
apt-get -y install git-core
cd ~
# ignore SSH host authenticity check
echo -e "Host github.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config
git clone git@github.com:jhibberd/battleships.git
ln -s ~/battleships/src/battleships /usr/local/lib/python2.7/dist-packages/battleships
mkdir /etc/battleships
ln -s ~/battleships/cfg/logging.yaml /etc/battleships/logging.yaml
ln -s ~/battleships/cfg/system.dev.yaml /etc/battleships/system.yaml

# run application
python battleships/src/battleships/main.py &

