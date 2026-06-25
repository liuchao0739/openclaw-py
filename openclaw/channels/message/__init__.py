"""Channel message — adapter, capabilities, state, runtime."""

from openclaw.channels.message.adapter import define_channel_message_adapter
from openclaw.channels.message.capabilities import derive_durable_final_delivery_requirements
from openclaw.channels.message.runtime import (
    DurableMessageSendState,
    classify_durable_send_recovery_state,
    create_durable_message_state_record,
)

__all__ = [
    "DurableMessageSendState",
    "classify_durable_send_recovery_state",
    "create_durable_message_state_record",
    "define_channel_message_adapter",
    "derive_durable_final_delivery_requirements",
]
