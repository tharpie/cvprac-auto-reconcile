# cvprac-auto-reconcile
a script using aristanetworks cvprac library to auto-reconcile nodes on a CloudVision cluster

1. Verify the following python libraries are installed
    1. cvprac

2. Setup cfg file with username/password on system where the script will be executed.
    1. sudo vim /etc/auto-reconcile.cfg

```
[authentication]
username='arista'
password='arista'

[cvp_instances]
nodes='node1,node2,node3'
```

3. Setup crontab entry to run on system

```
crontab -e

5 * * * * python auto-reconcile.py
```