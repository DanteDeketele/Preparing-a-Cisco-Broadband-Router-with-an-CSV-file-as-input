# Cisco broadband router CSV configurator

This project converts a semicolon-separated CSV file into Cisco IOS commands
that can be pasted into a router CLI. It follows the same layout as the Layer
2/3 switch assignment: a converter script, scenario examples, and generated
configuration files. The generated configuration includes the router behavior
needed for a broadband edge: WAN/LAN NAT roles, NAT overload, and DHCP pools
for directly connected LANs.

## CSV format

The header is:

```text
network;interface;description;vlan;ipaddress;subnetmask;defaultgateway
```

Use `wan` or `lan` for `network`. A physical interface uses VLAN `0`. A VLAN
greater than `0` creates a dot1Q subinterface such as `gi0/1.10` conceptually,
using the IOS command `encapsulation dot1Q 10` under the supplied interface.

Rows without an interface describe routed LAN networks and generate an
`ip route` command. Their `defaultgateway` is used as the next hop.

The converter also generates these commands automatically:

- WAN interfaces: `ip nat outside`
- LAN interfaces: `ip nat inside`
- LAN DHCP pools using the interface address as `default-router`
- NAT overload from the LAN networks to the first WAN interface
- A default route for a static WAN gateway

When the WAN address is `dhcp`, the router requests its address and gateway
from the upstream DHCP server. The generated DHCP pools are for clients on the
LAN side of the router, not for the WAN interface.

## Scenarios

- `examples/example-dhcp.csv`: WAN DHCP and one LAN interface
- `examples/example-static-wan.csv`: static WAN and one LAN interface
- `examples/example-routed-lans.csv`: one directly connected LAN and two static routes
- `examples/example-vlans.csv`: WAN DHCP and multiple VLAN subinterfaces

## Generate configuration

```powershell
python .\scripts\convert_csv_to_cisco_router_config.py `
    -f .\examples\example-vlans.csv `
    -o .\generated-config\example-vlans.txt
```

The output is plain text and can be reviewed before pasting into the router.
The converter accepts semicolon-separated files, like the neighboring switch
project, and comma-separated files with the same header.

## Validate all scenarios

```powershell
Get-ChildItem .\examples\*.csv | ForEach-Object {
    $output = ".\generated-config\$($_.BaseName).txt"
    python .\scripts\convert_csv_to_cisco_router_config.py -f $_.FullName -o $output
}
```

Review the generated commands carefully, especially the interface carrying
your management or SSH session. Configuration is not sent automatically.