Maak een python script die een tekstbestand produceert die je kan plakken op de CLI van de Cisco Router.

Het CSV-bestand kan er als volgt uitzien.
network 	interface 	description 	vlan 	ipaddress 	subnetmask 	defaultgateway
wan 	gi0/0 	WAN 	0 	dhcp 		
lan 	gi0/1 	LAN 	0 	192.168.1.1 	255.255.255.0 	
						
of 						
						
network 	interface 	description 	vlan 	ipaddress 	subnetmask 	defaultgateway
wan 	gi0/0 	WAN 	0 	172.23.80.200 	255.255.254.0 	172.23.80.1
lan 	gi0/1 	LAN 	0 	192.168.0.1 	255.255.255.0 	
						
of 						
						
network 	interface 	description 	vlan 	ipaddress 	subnetmask 	defaultgateway
wan 	gi0/0 	WAN 	0 	172.23.80.200 	255.255.254.0 	172.23.80.1
lan 	gi0/1 	Servers 	0 	192.168.0.254 	255.255.255.0 	
lan 		Accounting 	0 	192.168.2.0 	255.255.255.0 	192.168.0.1
lan 		HR 	0 	192.168.3.0 	255.255.255.0 	192.168.0.1
						
of 						
						
network 	interface 	description 	vlan 	ipaddress 	subnetmask 	defaultgateway
wan 	gi0/0 	WAN 	0 	dhcp 		
lan 	gi0/1 	Servers 	10 	192.168.10.254 	255.255.255.0 	
lan 	gi0/1 	Accounting 	20 	192.168.20.254 	255.255.255.0 	
lan 	gi0/1 	HR 	30 	192.168.30.254 	255.255.255.0 	
lan 	gi0/1 	Marketing 	40 	192.168.40.254 	255.255.255.0 	
lan 	gi0/1 	Production 	50 	192.168.50.254 	255.255.255.0 	

Probeer de verschillende scenario's uit !!!