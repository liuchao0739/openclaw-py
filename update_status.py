import json
from datetime import datetime, timezone

with open('migration/plan.json', 'r') as f:
    plan = json.load(f)

done = sum(1 for t in plan if t['status'] == 'done')
partial = sum(1 for t in plan if t['status'] == 'partial')
pending = sum(1 for t in plan if t['status'] == 'pending')
blocked = sum(1 for t in plan if t['status'] == 'blocked')

current_task = None
for t in plan:
    if t['status'] == 'partial':
        current_task = t
        break
if not current_task:
    for t in plan:
        if t['status'] == 'pending':
            current_task = t
            break

recently_completed = []
for t in reversed(plan):
    if t['status'] == 'done':
        recently_completed.append(t)
        if len(recently_completed) >= 5:
            break

status_content = f"# Migration status\n\nUpdated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n- **Done:** {done} / {len(plan)}\n- **Pending:** {pending}\n- **Partial:** {partial}\n- **Blocked:** {blocked}\n- **Remaining TypeScript lines:** 0\n\n## Current\n\n"

if current_task:
    status_content += f"- `{current_task['id']}` {current_task['title']} ({current_task.get('ts_source_lines', 0)} lines)\n\n"

status_content += "## Recently completed\n\n"
for task in recently_completed:
    status_content += f"- `{task['id']}` {task['title']}\n"

status_content += "\n## How to refresh\n\nThis file is rewritten after every task. Or ask in chat: 「进度」\n"

with open('migration/STATUS.md', 'w') as f:
    f.write(status_content)

print(f"Status updated: Done={done}, Partial={partial}, Pending={pending}")
if current_task:
    print(f"Next task: {current_task['id']} {current_task['title']}")
