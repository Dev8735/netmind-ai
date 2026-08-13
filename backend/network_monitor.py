"""
NetMind AI - Real-Time Network Monitor

Discovers and monitors SNMP-enabled network devices.

Supported device types:
    switch
    router
    firewall
    access_point
    server
    other

The interface count is dynamic. NetMind does NOT assume
16/24/48 ports.

SNMP v2c is used for the current lab/demo environment.
"""

import asyncio
import logging
from datetime import datetime

from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    get_cmd,
    walk_cmd,
)

from sqlalchemy.orm import sessionmaker

from app.models import (
    engine,
    NetworkDevice,
    NetworkInterface,
)


# ============================================================
# CONFIGURATION
# ============================================================

POLL_INTERVAL = 5

# Your local SNMP simulator
SNMP_HOST = "127.0.0.1"
SNMP_PORT = 1161
SNMP_COMMUNITY = "public"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("netmind-network-monitor")


# ============================================================
# DATABASE
# ============================================================

SessionLocal = sessionmaker(bind=engine)


# ============================================================
# SNMP HELPERS
# ============================================================

async def snmp_get(host, port, community, oid):
    """
    Perform one SNMP GET request.
    """

    snmp_engine = SnmpEngine()

    try:
        error_indication, error_status, error_index, var_binds = await get_cmd(
            snmp_engine,
            CommunityData(community, mpModel=1),
            await UdpTransportTarget.create(
                (host, port),
                timeout=2,
                retries=1,
            ),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        if error_indication:
            return None

        if error_status:
            return None

        for var_bind in var_binds:
            return str(var_bind[1])

        return None

    finally:
        snmp_engine.closeDispatcher()


async def snmp_walk(host, port, community, oid):
    """
    Walk an SNMP subtree and return:

        [(OID, value), ...]
    """

    results = []

    snmp_engine = SnmpEngine()

    try:
        async for (
            error_indication,
            error_status,
            error_index,
            var_binds,
        ) in walk_cmd(
            snmp_engine,
            CommunityData(community, mpModel=1),
            await UdpTransportTarget.create(
                (host, port),
                timeout=2,
                retries=1,
            ),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):

            if error_indication:
                logger.warning(
                    "SNMP error from %s:%s: %s",
                    host,
                    port,
                    error_indication,
                )
                break

            if error_status:
                logger.warning(
                    "SNMP error from %s:%s: %s",
                    host,
                    port,
                    error_status.prettyPrint(),
                )
                break

            for var_bind in var_binds:
                results.append(
                    (
                        str(var_bind[0]),
                        str(var_bind[1]),
                    )
                )

    finally:
        snmp_engine.closeDispatcher()

    return results


# ============================================================
# DEVICE DISCOVERY
# ============================================================

async def discover_device(host, port, community):
    """
    Discover basic device information.
    """

    sys_name = await snmp_get(
        host,
        port,
        community,
        "1.3.6.1.2.1.1.5.0",
    )

    sys_descr = await snmp_get(
        host,
        port,
        community,
        "1.3.6.1.2.1.1.1.0",
    )

    sys_uptime = await snmp_get(
        host,
        port,
        community,
        "1.3.6.1.2.1.1.3.0",
    )

    if not sys_name and not sys_descr:
        return None

    return {
        "name": sys_name or host,
        "description": sys_descr or "",
        "uptime": sys_uptime or "",
    }


# ============================================================
# INTERFACE DISCOVERY
# ============================================================

async def discover_interfaces(host, port, community):
    """
    Discover interfaces dynamically through IF-MIB.

    This means:

        16 ports -> 16 discovered interfaces
        24 ports -> 24 discovered interfaces
        48 ports -> 48 discovered interfaces

    No port count is hard-coded.
    """

    # IF-MIB::ifIndex
    indexes = await snmp_walk(
        host,
        port,
        community,
        "1.3.6.1.2.1.2.2.1.1",
    )

    if not indexes:
        return []

    interfaces = []

    for oid, value in indexes:

        try:
            if_index = int(oid.split(".")[-1])
        except ValueError:
            continue

        interfaces.append(
            {
                "if_index": if_index,
                "name": f"Interface-{if_index}",
            }
        )

    return interfaces


# ============================================================
# DATABASE DEVICE
# ============================================================

def get_or_create_device(
    session,
    name,
    device_type,
    vendor,
    model,
    host,
    port,
    community,
):
    device = (
        session.query(NetworkDevice)
        .filter(NetworkDevice.name == name)
        .first()
    )

    if device is None:

        device = NetworkDevice(
            name=name,
            device_type=device_type,
            vendor=vendor,
            model=model,
            ip_address=host,
            snmp_port=port,
            community=community,
            status="UNKNOWN",
        )

        session.add(device)
        session.commit()

        logger.info(
            "New network device discovered: %s",
            name,
        )

    return device


# ============================================================
# INTERFACE DATABASE
# ============================================================

def get_or_create_interface(
    session,
    device,
    if_index,
    name,
):
    interface = (
        session.query(NetworkInterface)
        .filter(
            NetworkInterface.device_id == device.id,
            NetworkInterface.if_index == if_index,
        )
        .first()
    )

    if interface is None:

        interface = NetworkInterface(
            device_id=device.id,
            if_index=if_index,
            name=name,
            admin_status="UNKNOWN",
            oper_status="UNKNOWN",
        )

        session.add(interface)
        session.commit()

        logger.info(
            "Discovered interface: %s / %s",
            device.name,
            name,
        )

    return interface


# ============================================================
# MONITOR DEVICE
# ============================================================

async def monitor_device(
    host,
    port,
    community,
    device_type="switch",
    vendor="Unknown",
    model=None,
):
    """
    Discover and continuously monitor one SNMP device.
    """

    session = SessionLocal()

    logger.info(
        "Starting monitoring for %s:%s",
        host,
        port,
    )

    # --------------------------------------------------------
    # Initial discovery
    # --------------------------------------------------------

    device_info = await discover_device(
        host,
        port,
        community,
    )

    if not device_info:

        logger.error(
            "Device %s:%s is unreachable through SNMP",
            host,
            port,
        )

        session.close()
        return

    device_name = device_info["name"]

    device = get_or_create_device(
        session=session,
        name=device_name,
        device_type=device_type,
        vendor=vendor,
        model=model,
        host=host,
        port=port,
        community=community,
    )

    device.status = "ONLINE"
    device.last_seen = datetime.utcnow()

    session.commit()

    logger.info(
        "Device ONLINE: %s",
        device_name,
    )

    # --------------------------------------------------------
    # Interface discovery
    # --------------------------------------------------------

    discovered_interfaces = await discover_interfaces(
        host,
        port,
        community,
    )

    logger.info(
        "%s interfaces discovered on %s",
        len(discovered_interfaces),
        device_name,
    )

    for item in discovered_interfaces:

        get_or_create_interface(
            session=session,
            device=device,
            if_index=item["if_index"],
            name=item["name"],
        )

    # --------------------------------------------------------
    # Continuous monitoring
    # --------------------------------------------------------

    previous_status = {}

    while True:

        try:

            # Check device availability
            current_name = await snmp_get(
                host,
                port,
                community,
                "1.3.6.1.2.1.1.5.0",
            )

            if current_name is None:

                if device.status != "OFFLINE":

                    logger.warning(
                        "DEVICE DOWN: %s",
                        device.name,
                    )

                device.status = "OFFLINE"
                session.commit()

                await asyncio.sleep(POLL_INTERVAL)
                continue

            # Device reachable
            device.status = "ONLINE"
            device.last_seen = datetime.utcnow()

            # ------------------------------------------------
            # Poll operational status
            # ------------------------------------------------

            status_rows = await snmp_walk(
                host,
                port,
                community,
                "1.3.6.1.2.1.2.2.1.8",
            )

            for oid, value in status_rows:

                try:
                    if_index = int(oid.split(".")[-1])
                except ValueError:
                    continue

                # Standard IF-MIB:
                # 1 = up
                # 2 = down
                # 3 = testing

                if value == "1":
                    current_status = "UP"
                elif value == "2":
                    current_status = "DOWN"
                elif value == "3":
                    current_status = "TESTING"
                else:
                    current_status = "UNKNOWN"

                interface = (
                    session.query(NetworkInterface)
                    .filter(
                        NetworkInterface.device_id == device.id,
                        NetworkInterface.if_index == if_index,
                    )
                    .first()
                )

                if interface is None:

                    interface = NetworkInterface(
                        device_id=device.id,
                        if_index=if_index,
                        name=f"Interface-{if_index}",
                    )

                    session.add(interface)
                    session.commit()

                old_status = previous_status.get(
                    if_index,
                    interface.oper_status,
                )

                # ------------------------------------------------
                # Detect state change
                # ------------------------------------------------

                if (
                    old_status not in ("UNKNOWN", None)
                    and old_status != current_status
                ):

                    logger.warning(
                        "INTERFACE STATE CHANGE | "
                        "%s | %s | %s -> %s",
                        device.name,
                        interface.name,
                        old_status,
                        current_status,
                    )

                interface.oper_status = current_status
                interface.last_seen = datetime.utcnow()

                previous_status[if_index] = current_status

            session.commit()

            await asyncio.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:

            logger.info(
                "Network monitor stopped."
            )

            break

        except Exception as exc:

            logger.exception(
                "Monitoring error: %s",
                exc,
            )

            await asyncio.sleep(POLL_INTERVAL)

    session.close()


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info(
        "=============================================="
    )

    logger.info(
        "NetMind Real-Time Network Monitor"
    )

    logger.info(
        "SNMP target: %s:%s",
        SNMP_HOST,
        SNMP_PORT,
    )

    logger.info(
        "Poll interval: %s seconds",
        POLL_INTERVAL,
    )

    logger.info(
        "=============================================="
    )

    await monitor_device(
        host=SNMP_HOST,
        port=SNMP_PORT,
        community=SNMP_COMMUNITY,
        device_type="switch",
        vendor="Lab",
        model="SNMP-Simulator",
    )


if __name__ == "__main__":
    asyncio.run(main())