from datetime import datetime

# Fault types that are SAFE to auto-remediate without human intervention.
# Deliberately conservative: only pure configuration/software actions that
# are fully reversible and carry no risk of masking a real hardware problem.
# Physical faults (cable removal, power failure, hardware faults) are
# intentionally excluded - those always require manual engineer action.
AUTO_REMEDIATION_ACTIONS = {
    "port_admin_shutdown": "no shutdown",
}


def is_auto_remediable(fault_type: str) -> bool:
    return fault_type in AUTO_REMEDIATION_ACTIONS


def attempt_remediation(fault_type: str, verification_command: str) -> dict:
    """
    Simulates executing an automated, safe fix for eligible fault types.
    Returns None if this fault type is not eligible (requires a human).
    """
    if not is_auto_remediable(fault_type):
        return None

    command_issued = AUTO_REMEDIATION_ACTIONS[fault_type]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log = (
        f"[{timestamp}] AUTOMATED REMEDIATION\n"
        f"Fault type '{fault_type}' is eligible for zero-touch fix.\n"
        f"Command issued: {command_issued}\n"
        f"Re-verifying with: {verification_command}\n"
        f"Result: Fault cleared automatically. No engineer action required."
    )

    return {
        "command_issued": command_issued,
        "timestamp": timestamp,
        "log": log
    }