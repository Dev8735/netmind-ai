# NetMind AI — Fault Taxonomy

## Switch Faults
- **switch_network_down** — Switch unreachable, but device itself may still be powered (network-layer issue)
- **switch_power_shutdown** — Switch completely powered off (no LEDs, no response at all)

## Port Faults
- **port_error_flap** — Port cycling up/down repeatedly due to errors (CRC errors, faulty hardware, signal issues)
- **port_admin_shutdown** — Port intentionally disabled via `shutdown` command (administrative action, not a fault)
- **port_cable_removal** — Physical cable disconnected (link down, no errors, just absence of signal)

## Why this distinction matters
These look similar on the surface ("port is down") but have completely different root causes and solutions:
- Admin shutdown → just needs `no shutdown`, not a real incident
- Cable removal → physical check needed, not a software fix
- Error flap → needs hardware/cable diagnostics, ongoing instability
- Power shutdown → PSU/power check, most severe
- Network down (but powered) → routing/config issue, not hardware