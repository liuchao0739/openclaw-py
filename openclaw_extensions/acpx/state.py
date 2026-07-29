ACPX_PROCESS_LEASE_NAMESPACE = "process-leases"
ACPX_PROCESS_LEASE_MAX_ENTRIES = 4096
ACPX_LEGACY_PROCESS_LEASE_FILE = "process-leases.json"

ACPX_GATEWAY_INSTANCE_NAMESPACE = "gateway-instance"
ACPX_GATEWAY_INSTANCE_KEY = "current"
ACPX_GATEWAY_INSTANCE_MAX_ENTRIES = 1
ACPX_LEGACY_GATEWAY_INSTANCE_FILE = "gateway-instance-id"


def normalize_acpx_gateway_instance_record(value):
    if not isinstance(value, dict):
        return None
    instance_id = value.get("instanceId")
    if not isinstance(instance_id, str) or not instance_id.strip():
        return None
    raw_created_at = value.get("createdAt")
    if isinstance(raw_created_at, (int, float)) and not isinstance(raw_created_at, bool) and raw_created_at == raw_created_at:
        created_at = int(raw_created_at)
    else:
        created_at = 0
    return {
        "instanceId": instance_id.strip(),
        "createdAt": created_at,
    }
