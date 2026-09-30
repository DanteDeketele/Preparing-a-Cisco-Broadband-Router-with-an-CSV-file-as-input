import argparse
import csv
import ipaddress
import re
from pathlib import Path


REQUIRED_COLUMNS = {
    "network",
    "interface",
    "description",
    "vlan",
    "ipaddress",
    "subnetmask",
    "defaultgateway",
}


def get_parameters():
    parser = argparse.ArgumentParser(
        description="Convert a Cisco router CSV file to IOS configuration text."
    )
    parser.add_argument("-f", "--file", required=True, help="Input CSV file")
    parser.add_argument("-o", "--output", required=True, help="Output text file")
    parser.add_argument("-hn", "--hostname", default="Router", help="Router hostname")
    return parser.parse_args()


class RouterLine:
    def __init__(self, row):
        self.network = row["network"].strip().lower()
        self.interface = row["interface"].strip()
        self.description = row["description"].strip()
        self.vlan = row["vlan"].strip()
        self.ip_address = row["ipaddress"].strip().lower()
        self.subnet_mask = row["subnetmask"].strip()
        self.default_gateway = row["defaultgateway"].strip()
        self.vlan_id = int(self.vlan or "0")

    @property
    def is_static_route(self):
        return not self.interface and bool(self.ip_address and self.subnet_mask)

    @property
    def is_subinterface(self):
        return bool(self.interface and self.vlan_id)

    @property
    def is_default_route(self):
        return self.network == "wan" and bool(self.default_gateway)

    def validate(self):
        if self.network not in {"wan", "lan"}:
            return "network must be 'wan' or 'lan'"
        if not self.description:
            return "description cannot be empty"
        if self.vlan_id < 0 or self.vlan_id > 4094:
            return "vlan must be between 0 and 4094"
        if self.is_static_route:
            if self.network != "lan":
                return "rows without an interface must be LAN routes"
            if not self.default_gateway:
                return "a static route requires defaultgateway"
        elif not self.interface:
            return "interface cannot be empty unless this is a static route"
        if self.ip_address == "dhcp":
            if self.subnet_mask or self.default_gateway:
                return "dhcp rows cannot contain a subnetmask or defaultgateway"
        elif self.ip_address:
            try:
                ipaddress.IPv4Address(self.ip_address)
            except ValueError:
                return f"invalid IPv4 address: {self.ip_address}"
            if not self.subnet_mask:
                return "a static IP address requires subnetmask"
        elif self.subnet_mask:
            return "subnetmask requires an IP address"
        if self.subnet_mask:
            try:
                ipaddress.IPv4Network(f"0.0.0.0/{self.subnet_mask}")
            except ValueError:
                return f"invalid subnetmask: {self.subnet_mask}"
        if self.default_gateway:
            try:
                ipaddress.IPv4Address(self.default_gateway)
            except ValueError:
                return f"invalid defaultgateway: {self.default_gateway}"
        if self.is_subinterface and self.ip_address == "dhcp":
            return "dhcp is only supported on physical interfaces"
        if self.is_static_route and self.vlan_id:
            return "static routes cannot have a vlan"
        return None


def read_rows(input_path):
    with input_path.open(newline="", encoding="utf-8-sig") as input_file:
        sample = input_file.read(2048)
        input_file.seek(0)
        delimiter = ";" if ";" in sample else ","
        rows = csv.DictReader(input_file, delimiter=delimiter)
        fieldnames = {field.strip().lower() for field in rows.fieldnames or []}
        if fieldnames != REQUIRED_COLUMNS:
            missing = ", ".join(sorted(REQUIRED_COLUMNS - fieldnames))
            extra = ", ".join(sorted(fieldnames - REQUIRED_COLUMNS))
            details = []
            if missing:
                details.append(f"missing columns: {missing}")
            if extra:
                details.append(f"unknown columns: {extra}")
            raise SystemExit("CSV header is invalid: " + "; ".join(details))
        result = []
        errors = []
        for row_number, row in enumerate(rows, start=2):
            if None in row:
                errors.append(f"CSV row {row_number}: too many fields")
                continue
            normalized = {
                key.strip().lower(): (value or "")
                for key, value in row.items()
            }
            try:
                config_line = RouterLine(normalized)
            except (KeyError, ValueError) as error:
                errors.append(f"CSV row {row_number}: {error}")
                continue
            validation_error = config_line.validate()
            if validation_error:
                errors.append(f"CSV row {row_number}: {validation_error}")
            else:
                result.append(config_line)
        if errors:
            raise SystemExit("CSV validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        return result


def interface_commands(config_line):
    interface_name = get_interface_name(config_line)
    commands = [f"interface {interface_name}"]
    if config_line.network == "wan":
        commands.append(" ip nat outside")
    elif config_line.network == "lan":
        commands.append(" ip nat inside")
    if config_line.is_subinterface:
        commands.append(f" encapsulation dot1Q {config_line.vlan_id}")
    commands.append(f" description {config_line.description}")
    if config_line.ip_address == "dhcp":
        commands.append(" ip address dhcp")
    elif config_line.ip_address:
        commands.append(f" ip address {config_line.ip_address} {config_line.subnet_mask}")
    else:
        commands.append(" no ip address")
    commands.append(" no shutdown")
    commands.append("exit")
    return commands


def get_interface_name(config_line):
    if config_line.is_subinterface:
        return f"{config_line.interface}.{config_line.vlan_id}"
    return config_line.interface


def route_commands(config_line):
    if config_line.is_default_route:
        return [f"ip route 0.0.0.0 0.0.0.0 {config_line.default_gateway}"]
    network = ipaddress.IPv4Network(
        f"{config_line.ip_address}/{config_line.subnet_mask}", strict=False
    )
    return [
        f"ip route {network.network_address} {config_line.subnet_mask} {config_line.default_gateway}"
    ]


def get_network(config_line):
    return ipaddress.IPv4Network(
        f"{config_line.ip_address}/{config_line.subnet_mask}", strict=False
    )


def get_dhcp_pool_name(config_line):
    pool_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", config_line.description).strip("-")
    return pool_name.lower() or "lan"


def global_commands(config_lines):
    commands = []
    wan_lines = [
        line for line in config_lines
        if line.network == "wan" and line.interface
    ]
    lan_lines = [
        line for line in config_lines
        if line.network == "lan" and line.interface and line.ip_address not in {"", "dhcp"}
    ]
    route_lines = [
        line for line in config_lines
        if line.is_static_route
    ]

    if wan_lines and lan_lines:
        commands.extend([
            "! NAT overload for LAN clients using the WAN interface",
            "access-list 1 remark LAN networks allowed to use the WAN",
        ])
        for line in lan_lines + route_lines:
            network = get_network(line)
            wildcard = ipaddress.IPv4Address(int(network.hostmask))
            commands.append(f"access-list 1 permit {network.network_address} {wildcard}")
        wan_interface = get_interface_name(wan_lines[0])
        commands.append(f"ip nat inside source list 1 interface {wan_interface} overload")
        commands.append("")

    for line in lan_lines:
        network = get_network(line)
        commands.extend([
            f"ip dhcp excluded-address {line.ip_address}",
            f"ip dhcp pool {get_dhcp_pool_name(line)}",
            f" network {network.network_address} {line.subnet_mask}",
            f" default-router {line.ip_address}",
            " exit",
            "",
        ])
    return commands


def build_configuration(config_lines, hostname):
    commands = ["! Cisco broadband router configuration", f"hostname {hostname}", ""]
    commands.extend(global_commands(config_lines))
    subinterface_lines = [line for line in config_lines if line.is_subinterface]
    if subinterface_lines:
        commands.extend(["! VLAN subinterfaces use dot1Q tagging", ""])
        parent_interfaces = sorted({line.interface for line in subinterface_lines})
        for interface_name in parent_interfaces:
            commands.extend([
                f"interface {interface_name}",
                " no ip address",
                " no shutdown",
                "exit",
                "",
            ])
    for config_line in config_lines:
        if config_line.is_static_route or config_line.is_default_route:
            if config_line.is_default_route:
                commands.extend(interface_commands(config_line))
            commands.extend(route_commands(config_line))
        else:
            commands.extend(interface_commands(config_line))
        commands.append("")
    return commands


def main():
    arguments = get_parameters()
    input_path = Path(arguments.file)
    output_path = Path(arguments.output)
    if not input_path.is_file():
        raise SystemExit(f"Error: input file not found: {input_path}")
    config_lines = read_rows(input_path)
    if not config_lines:
        raise SystemExit("Input CSV contains no configuration rows")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(build_configuration(config_lines, arguments.hostname)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()