"""
NetMind AI - Network Lab Simulator

Simulates a realistic enterprise/industrial network environment.

Devices:
    - Core Switch       : 48 interfaces
    - Access Switch     : 24 interfaces
    - Access Switch     : 16 interfaces
    - Core Router       : 8 interfaces
    - Firewall          : 8 interfaces
    - Wireless AP       : 2 interfaces
    - Server            : 2 interfaces

The simulator stores devices/interfaces in the NetMind database.

When an interface changes state, it sends an RFC 5424-compatible
Syslog event to the EXISTING NetMind syslog_listener.py:

    UDP 127.0.0.1:5140

Flow:

    Network Lab
        ↓
    Interface state change
        ↓
    Syslog
        ↓
    syslog_listener.py
        ↓
    NLP Parser
        ↓
    Diagnosis Engine
        ↓
    Correlation Engine
        ↓
    Incident + Signal
        ↓
    Dashboard
"""

import sys
import socket
from datetime import datetime

from sqlalchemy.orm import sessionmaker


# ============================================================
# BACKEND IMPORT
# ============================================================

sys.path.append(
    r"C:\Internship\netmind-ai\backend"
)

from app.models import (
    engine,
    NetworkDevice,
    NetworkInterface,
)


# ============================================================
# DATABASE
# ============================================================

SessionLocal = sessionmaker(bind=engine)


# ============================================================
# SYSLOG CONFIGURATION
# ============================================================

SYSLOG_HOST = "127.0.0.1"
SYSLOG_PORT = 5140


# ============================================================
# NETWORK DEVICES
# ============================================================

DEVICES = [
    {
        "name": "SW-CORE-01",
        "type": "switch",
        "vendor": "Cisco",
        "model": "Core-Switch",
        "ip": "10.10.1.10",
        "interfaces": 48,
    },
    {
        "name": "SW-ACCESS-01",
        "type": "switch",
        "vendor": "Cisco",
        "model": "Access-Switch",
        "ip": "10.10.1.11",
        "interfaces": 24,
    },
    {
        "name": "SW-ACCESS-02",
        "type": "switch",
        "vendor": "Cisco",
        "model": "Access-Switch",
        "ip": "10.10.1.12",
        "interfaces": 16,
    },
    {
        "name": "RTR-CORE-01",
        "type": "router",
        "vendor": "Cisco",
        "model": "Core-Router",
        "ip": "10.10.1.1",
        "interfaces": 8,
    },
    {
        "name": "FW-MAIN-01",
        "type": "firewall",
        "vendor": "Enterprise",
        "model": "Firewall",
        "ip": "10.10.1.2",
        "interfaces": 8,
    },
    {
        "name": "AP-FLOOR-01",
        "type": "access_point",
        "vendor": "Enterprise",
        "model": "Wireless-AP",
        "ip": "10.10.1.20",
        "interfaces": 2,
    },
    {
        "name": "SERVER-01",
        "type": "server",
        "vendor": "Linux",
        "model": "Application-Server",
        "ip": "10.10.1.30",
        "interfaces": 2,
    },
]


# ============================================================
# INTERFACE NAME GENERATOR
# ============================================================

def interface_name(device_type, number):
    """
    Generate realistic interface names according to
    device category.
    """

    if device_type == "switch":
        return f"Gi1/0/{number}"

    if device_type == "router":
        return f"GigabitEthernet0/{number}"

    if device_type == "firewall":
        return f"port{number}"

    if device_type == "access_point":
        return f"eth{number - 1}"

    if device_type == "server":
        return f"eth{number - 1}"

    return f"Interface-{number}"


# ============================================================
# SYSLOG SENDER
# ============================================================

def send_syslog(device, status, message):
    """
    Send an RFC 5424-compatible Syslog message to
    the existing NetMind Syslog listener.

    Expected payload:

        device|STATUS|message
    """

    timestamp = datetime.utcnow().strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    hostname = "netmind-network-lab"
    appname = "netmind-lab"
    procid = "-"
    msgid = "-"
    structured_data = "-"

    payload = (
        f"{device}|{status}|{message}"
    )

    packet = (
        f"<134>1 "
        f"{timestamp} "
        f"{hostname} "
        f"{appname} "
        f"{procid} "
        f"{msgid} "
        f"{structured_data} "
        f"{payload}"
    )

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    try:

        sock.sendto(
            packet.encode("utf-8"),
            (
                SYSLOG_HOST,
                SYSLOG_PORT,
            ),
        )

        print(
            f"[SYSLOG] "
            f"{device} | "
            f"{status} | "
            f"{message}"
        )

    except Exception as exc:

        print(
            f"[SYSLOG ERROR] "
            f"Could not send event: {exc}"
        )

    finally:

        sock.close()


# ============================================================
# CREATE NETWORK TOPOLOGY
# ============================================================

def create_topology():

    session = SessionLocal()

    print()
    print("=" * 65)
    print("              NETMIND NETWORK LAB")
    print("=" * 65)

    for config in DEVICES:

        device = (
            session.query(NetworkDevice)
            .filter(
                NetworkDevice.name
                == config["name"]
            )
            .first()
        )

        # ----------------------------------------------------
        # CREATE DEVICE
        # ----------------------------------------------------

        if device is None:

            device = NetworkDevice(
                name=config["name"],
                device_type=config["type"],
                vendor=config["vendor"],
                model=config["model"],
                ip_address=config["ip"],
                snmp_port=161,
                community="public",
                status="ONLINE",
                last_seen=datetime.utcnow(),
            )

            session.add(device)
            session.commit()

            print(
                f"[DEVICE CREATED] "
                f"{config['name']:<18} "
                f"{config['type']:<14} "
                f"{config['interfaces']:>2} interfaces"
            )

        else:

            device.status = "ONLINE"
            device.last_seen = datetime.utcnow()

            print(
                f"[DEVICE EXISTS]  "
                f"{config['name']}"
            )

        # ----------------------------------------------------
        # CREATE INTERFACES
        # ----------------------------------------------------

        for number in range(
            1,
            config["interfaces"] + 1,
        ):

            existing = (
                session.query(NetworkInterface)
                .filter(
                    NetworkInterface.device_id
                    == device.id,
                    NetworkInterface.if_index
                    == number,
                )
                .first()
            )

            if existing is None:

                interface = NetworkInterface(
                    device_id=device.id,
                    if_index=number,
                    name=interface_name(
                        config["type"],
                        number,
                    ),
                    description=(
                        f"{config['name']} "
                        f"interface {number}"
                    ),
                    admin_status="UP",
                    oper_status="UP",
                    speed=1_000_000_000,
                    in_octets=0,
                    out_octets=0,
                    in_errors=0,
                    out_errors=0,
                    last_seen=datetime.utcnow(),
                )

                session.add(interface)

        session.commit()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_devices = (
        session.query(NetworkDevice).count()
    )

    total_interfaces = (
        session.query(NetworkInterface).count()
    )

    print()
    print("=" * 65)
    print("NETWORK LAB READY")
    print("=" * 65)

    print(
        f"Devices     : {total_devices}"
    )

    print(
        f"Interfaces  : {total_interfaces}"
    )

    print()
    print("Topology:")
    print()
    print("                 RTR-CORE-01")
    print("                       |")
    print("                  FW-MAIN-01")
    print("                       |")
    print("                  SW-CORE-01")
    print("                 /             \\")
    print("        SW-ACCESS-01       SW-ACCESS-02")
    print("             |")
    print("        AP-FLOOR-01")
    print("             |")
    print("         SERVER-01")
    print()

    session.close()


# ============================================================
# SHOW DEVICES
# ============================================================

def show_devices():

    session = SessionLocal()

    devices = (
        session.query(NetworkDevice)
        .all()
    )

    print()
    print("=" * 85)
    print("NETWORK DEVICES")
    print("=" * 85)

    print(
        f"{'DEVICE':<20}"
        f"{'TYPE':<16}"
        f"{'STATUS':<12}"
        f"{'INTERFACES':>12}"
    )

    print("-" * 85)

    for device in devices:

        interface_count = (
            session.query(NetworkInterface)
            .filter(
                NetworkInterface.device_id
                == device.id
            )
            .count()
        )

        print(
            f"{device.name:<20}"
            f"{device.device_type:<16}"
            f"{device.status:<12}"
            f"{interface_count:>12}"
        )

    print()

    session.close()


# ============================================================
# SHOW INTERFACES
# ============================================================

def show_interfaces(device_name):

    session = SessionLocal()

    device = (
        session.query(NetworkDevice)
        .filter(
            NetworkDevice.name
            == device_name
        )
        .first()
    )

    if device is None:

        print(
            f"Device not found: {device_name}"
        )

        session.close()
        return

    interfaces = (
        session.query(NetworkInterface)
        .filter(
            NetworkInterface.device_id
            == device.id
        )
        .order_by(
            NetworkInterface.if_index
        )
        .all()
    )

    print()
    print(
        f"INTERFACES: {device.name}"
    )

    print("-" * 80)

    print(
        f"{'ID':>4} "
        f"{'NAME':<25} "
        f"{'ADMIN':<10} "
        f"{'OPER':<10}"
    )

    print("-" * 80)

    for interface in interfaces:

        print(
            f"{interface.if_index:>4} "
            f"{interface.name:<25} "
            f"{interface.admin_status:<10} "
            f"{interface.oper_status:<10}"
        )

    print()

    session.close()


# ============================================================
# CHANGE INTERFACE STATE
# ============================================================

def set_interface(
    device_name,
    interface_number,
    status,
):

    session = SessionLocal()

    # --------------------------------------------------------
    # Find device
    # --------------------------------------------------------

    device = (
        session.query(NetworkDevice)
        .filter(
            NetworkDevice.name
            == device_name
        )
        .first()
    )

    if device is None:

        print(
            f"Device not found: "
            f"{device_name}"
        )

        session.close()
        return

    # --------------------------------------------------------
    # Find interface
    # --------------------------------------------------------

    interface = (
        session.query(NetworkInterface)
        .filter(
            NetworkInterface.device_id
            == device.id,
            NetworkInterface.if_index
            == interface_number,
        )
        .first()
    )

    if interface is None:

        print(
            f"Interface {interface_number} "
            f"not found on {device_name}"
        )

        session.close()
        return

    # --------------------------------------------------------
    # Previous state
    # --------------------------------------------------------

    old_status = interface.oper_status
    new_status = status.upper()

    # --------------------------------------------------------
    # Ignore duplicate command
    # --------------------------------------------------------

    if old_status == new_status:

        print(
            f"[NO CHANGE] "
            f"{device_name} / "
            f"{interface.name} "
            f"is already {new_status}"
        )

        session.close()
        return

    # --------------------------------------------------------
    # Update database
    # --------------------------------------------------------

    interface.oper_status = new_status
    interface.last_seen = datetime.utcnow()

    session.commit()

    # --------------------------------------------------------
    # Display event
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("INTERFACE STATE CHANGE")
    print("=" * 65)

    print(
        f"Device    : {device.name}"
    )

    print(
        f"Interface : {interface.name}"
    )

    print(
        f"Previous  : {old_status}"
    )

    print(
        f"Current   : {new_status}"
    )

    print("=" * 65)

    # --------------------------------------------------------
    # FAULT EVENT
    # --------------------------------------------------------

    if new_status == "DOWN":

        message = (
            f"Interface {interface.name} "
            f"on {device.name} changed from "
            f"{old_status} to DOWN; "
            f"possible network link failure"
        )

        send_syslog(
            device=device.name,
            status="FAULT",
            message=message,
        )

    # --------------------------------------------------------
    # RECOVERY EVENT
    # --------------------------------------------------------

    elif new_status == "UP":

        message = (
            f"Interface {interface.name} "
            f"on {device.name} recovered "
            f"from {old_status} to UP"
        )

        send_syslog(
            device=device.name,
            status="OK",
            message=message,
        )

    session.close()


# ============================================================
# DEVICE DOWN SIMULATION
# ============================================================

def set_device_status(
    device_name,
    status,
):

    session = SessionLocal()

    device = (
        session.query(NetworkDevice)
        .filter(
            NetworkDevice.name
            == device_name
        )
        .first()
    )

    if device is None:

        print(
            f"Device not found: "
            f"{device_name}"
        )

        session.close()
        return

    old_status = device.status
    new_status = status.upper()

    if old_status == new_status:

        print(
            f"[NO CHANGE] "
            f"{device.name} "
            f"is already {new_status}"
        )

        session.close()
        return

    device.status = new_status
    device.last_seen = datetime.utcnow()

    session.commit()

    print()
    print("=" * 65)
    print("DEVICE STATE CHANGE")
    print("=" * 65)

    print(
        f"Device   : {device.name}"
    )

    print(
        f"Previous : {old_status}"
    )

    print(
        f"Current  : {new_status}"
    )

    print("=" * 65)

    if new_status == "OFFLINE":

        message = (
            f"Network device {device.name} "
            f"is unreachable and appears to be offline"
        )

        send_syslog(
            device=device.name,
            status="FAULT",
            message=message,
        )

    elif new_status == "ONLINE":

        message = (
            f"Network device {device.name} "
            f"has recovered and is online"
        )

        send_syslog(
            device=device.name,
            status="OK",
            message=message,
        )

    session.close()


# ============================================================
# COMMAND HELP
# ============================================================

def show_help():

    print()
    print("Available commands:")
    print()
    print("  devices")
    print(
        "      Show all network devices"
    )
    print()
    print(
        "  interfaces <device>"
    )
    print(
        "      Show all interfaces of a device"
    )
    print()
    print(
        "  down <device> <interface>"
    )
    print(
        "      Simulate interface failure"
    )
    print()
    print(
        "  up <device> <interface>"
    )
    print(
        "      Restore interface"
    )
    print()
    print(
        "  device-down <device>"
    )
    print(
        "      Simulate complete device failure"
    )
    print()
    print(
        "  device-up <device>"
    )
    print(
        "      Restore complete device"
    )
    print()
    print("  help")
    print("      Show this help")
    print()
    print("  exit")
    print()


# ============================================================
# MAIN MENU
# ============================================================

def main():

    create_topology()

    show_help()

    while True:

        try:

            command = input(
                "netmind-lab> "
            ).strip()

        except KeyboardInterrupt:

            print()
            print(
                "Network Lab stopped."
            )

            break

        if not command:
            continue

        parts = command.split()

        command_name = (
            parts[0].lower()
        )

        # ----------------------------------------------------
        # DEVICES
        # ----------------------------------------------------

        if command_name == "devices":

            show_devices()

        # ----------------------------------------------------
        # INTERFACES
        # ----------------------------------------------------

        elif command_name == "interfaces":

            if len(parts) != 2:

                print(
                    "Usage: "
                    "interfaces SW-CORE-01"
                )

                continue

            show_interfaces(
                parts[1]
            )

        # ----------------------------------------------------
        # INTERFACE DOWN / UP
        # ----------------------------------------------------

        elif command_name in (
            "down",
            "up",
        ):

            if len(parts) != 3:

                print(
                    "Usage: "
                    "down SW-CORE-01 17"
                )

                continue

            device_name = parts[1]

            try:

                interface_number = int(
                    parts[2]
                )

            except ValueError:

                print(
                    "Interface number must "
                    "be numeric."
                )

                continue

            if command_name == "down":

                status = "DOWN"

            else:

                status = "UP"

            set_interface(
                device_name,
                interface_number,
                status,
            )

        # ----------------------------------------------------
        # DEVICE DOWN / UP
        # ----------------------------------------------------

        elif command_name in (
            "device-down",
            "device-up",
        ):

            if len(parts) != 2:

                print(
                    "Usage: "
                    "device-down RTR-CORE-01"
                )

                continue

            if command_name == "device-down":

                status = "OFFLINE"

            else:

                status = "ONLINE"

            set_device_status(
                parts[1],
                status,
            )

        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------

        elif command_name == "help":

            show_help()

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        elif command_name == "exit":

            print(
                "NetMind Network Lab stopped."
            )

            break

        else:

            print(
                "Unknown command. "
                "Type 'help'."
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()