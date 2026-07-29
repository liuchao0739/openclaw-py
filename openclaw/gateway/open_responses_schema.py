"""OpenResponses API Zod Schemas

Mirrors src/gateway/open-responses.schema.ts.
"""

from __future__ import annotations

from typing import Any

input_text_content_part_schema: Any = None
output_text_content_part_schema: Any = None
input_image_source_schema: Any = None
input_image_content_part_schema: Any = None
input_file_source_schema: Any = None
input_file_content_part_schema: Any = None
content_part_schema: Any = None
message_item_role_schema: Any = None
assistant_phase_schema: Any = None
message_item_schema: Any = None
function_call_item_schema: Any = None
function_call_output_item_schema: Any = None
reasoning_item_schema: Any = None
item_reference_item_schema: Any = None
item_param_schema: Any = None
function_tool_definition_schema: Any = None
tool_definition_schema: Any = None
tool_choice_schema: Any = None
create_response_body_schema: Any = None
response_status_schema: Any = None
output_item_schema: Any = None
usage_schema: Any = None
response_resource_schema: Any = None
response_created_event_schema: Any = None
response_in_progress_event_schema: Any = None
response_completed_event_schema: Any = None
response_failed_event_schema: Any = None
output_item_added_event_schema: Any = None
output_item_done_event_schema: Any = None
content_part_added_event_schema: Any = None
content_part_done_event_schema: Any = None
output_text_delta_event_schema: Any = None
output_text_done_event_schema: Any = None

ContentPart = Any
AssistantPhase = Any
ItemParam = Any
ToolDefinition = Any
CreateResponseBody = Any
ResponseStatus = Any
OutputItem = Any
Usage = Any
ResponseResource = Any
StreamingEvent = Any

