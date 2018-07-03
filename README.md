# cvprac-auto-reconcile
a script using aristanetworks cvprac library to auto-reconcile nodes on a CloudVision cluster

1. Verify the following python libraries are installed

    a. cvprac

2. Setup cfg file with username/password

    a. touch /etc/auto-reconcile.cfg

    b. vim /etc/auto-reconcile.cfg

        [authentication]
        username='arista'
        password='arista'

        [cvp_instances]
        nodes='node1,node2,node3'

3. Setup crontab entry to run on system
        
        crontab -e

        x x x x x auto-reconcile.py

