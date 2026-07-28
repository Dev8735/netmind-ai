"""
Safely rewords the 3 KB rows tagged 'port_admin_shutdown' so their
incident_description/symptoms text more closely matches how real
incidents get phrased (e.g. "administratively shut down", "no errors")
instead of the more generic original wording that was losing the
embedding-similarity match to an unrelated 'port security violation' row.

Only rows where fault_type == 'port_admin_shutdown' are touched.
All other rows in the CSV are copied through unchanged, byte-for-byte
in terms of field values (csv module handles quoting/escaping).

Usage:
    python fix_kb_wording.py data/knowledge_base.csv
"""
import csv
import sys
import shutil

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_kb_wording.py <path_to_knowledge_base.csv>")
        sys.exit(1)

    path = sys.argv[1]
    backup_path = path + ".bak"
    shutil.copy(path, backup_path)
    print(f"Backup saved to {backup_path}")

    # New wording per possible_cause, keyed so each of the 3 rows gets
    # phrasing that distinguishes it while still matching real incident text.
    NEW_TEXT = {
        "Port manually shut down via configuration": {
            "incident_description": "Port on switch is administratively shut down",
            "symptoms": "No errors, interface admin down, no traffic passing, port disabled via configuration",
        },
        "Automated script disabled port for maintenance": {
            "incident_description": "Port on switch is administratively shut down",
            "symptoms": "No errors, interface admin down, disabled automatically during maintenance window",
        },
        "Security policy auto-disabled port": {
            "incident_description": "Port on switch is administratively shut down",
            "symptoms": "No errors, interface admin down, disabled by port security policy",
        },
    }

    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("fault_type") == "port_admin_shutdown" and row.get("possible_cause") in NEW_TEXT:
                new_vals = NEW_TEXT[row["possible_cause"]]
                row["incident_description"] = new_vals["incident_description"]
                row["symptoms"] = new_vals["symptoms"]
                print(f"Updated row: possible_cause='{row['possible_cause']}'")
            rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {path} updated in place. Original backed up at {backup_path}.")

if __name__ == "__main__":
    main()