# ClickUp API Data Structures

## Team Member JSON Structure
```json
{
  "user": {
    "id": 101423859,
    "username": "MD Anamul Hasan",
    "email": "anamul.arboraistudio@gmail.com",
    "color": "#795548",
    "profilePicture": null,
    "initials": "MH",
    "role": 3,
    "role_subtype": 0,
    "role_key": "member",
    "custom_role": null,
    "last_active": "1756090099589",
    "date_joined": "1755574897635",
    "date_invited": "1755574476936"
  },
  "invited_by": {
    "id": 218438989,
    "username": "Tahsin Ridwan Pulok",
    "color": null,
    "email": "tahsin.arboraistudio@gmail.com",
    "initials": "TP",
    "profilePicture": "https://attachments.clickup.com/profilePictures/218438989_uS3.jpg",
    "banned_date": null,
    "status": "active"
  }
}
```

## Task JSON Structure
```json
{
  "id": "86eum77f3",
  "custom_id": null,
  "custom_item_id": 0,
  "name": "Private Beta Testing 2.0",
  "text_content": "",
  "description": "",
  "status": {
    "status": "complete",
    "id": "sc901810288401_wNdmBHSh",
    "color": "#008844",
    "type": "closed",
    "orderindex": 2
  },
  "orderindex": "120476343.00025360000000000000000000000000",
  "date_created": "1756147688760",
  "date_updated": "1756148466069",
  "date_closed": "1756148466069",
  "date_done": "1756148466069",
  "archived": false,
  "creator": {
    "id": 224412174,
    "username": "Istiak Ahmed",
    "color": null,
    "email": "istiak.arboraistudio@gmail.com",
    "profilePicture": "https://attachments.clickup.com/profilePictures/224412174_0b0.jpg"
  },
  "assignees": [
    {
      "id": 224412174,
      "username": "Istiak Ahmed",
      "color": null,
      "initials": "IA",
      "email": "istiak.arboraistudio@gmail.com",
      "profilePicture": "https://attachments.clickup.com/profilePictures/224412174_0b0.jpg"
    }
  ],
  "group_assignees": [],
  "watchers": [
    {
      "id": 101423859,
      "username": "MD Anamul Hasan",
      "color": "#795548",
      "initials": "MH",
      "email": "anamul.arboraistudio@gmail.com",
      "profilePicture": null
    },
    {
      "id": 224412174,
      "username": "Istiak Ahmed",
      "color": null,
      "initials": "IA",
      "email": "istiak.arboraistudio@gmail.com",
      "profilePicture": "https://attachments.clickup.com/profilePictures/224412174_0b0.jpg"
    }
  ],
  "checklists": [],
  "tags": [],
  "parent": null,
  "top_level_parent": null,
  "priority": null,
  "due_date": null,
  "start_date": null,
  "points": null,
  "time_estimate": null,
  "custom_fields": [
    {
      "id": "ce86a517-6f98-436f-9cbe-9ef1b86c870a",
      "name": "Track Time",
      "type": "short_text",
      "type_config": {},
      "date_created": "1754399693368",
      "hide_from_guests": false,
      "required": false
    }
  ],
  "dependencies": [],
  "linked_tasks": [],
  "locations": [],
  "team_id": "90181529208",
  "url": "https://app.clickup.com/t/86eum77f3",
  "sharing": {
    "public": false,
    "public_share_expires_on": null,
    "public_fields": [
      "assignees",
      "priority",
      "due_date",
      "content",
      "comments",
      "attachments",
      "customFields",
      "subtasks",
      "tags",
      "checklists",
      "coverimage"
    ],
    "token": null,
    "seo_optimized": false
  },
  "permission_level": "create",
  "list": {
    "id": "901810288401",
    "name": "General Task List",
    "access": true
  },
  "project": {
    "id": "90186921419",
    "name": "hidden",
    "hidden": true,
    "access": true
  },
  "folder": {
    "id": "90186921419",
    "name": "hidden",
    "hidden": true,
    "access": true
  },
  "space": {
    "id": "90186043695"
  }
}
```

## Key Fields Summary

### Team Member Fields:
- `user.id`: Unique user ID
- `user.username`: Display name
- `user.email`: Email address
- `user.role_key`: Role type (member, admin, owner, guest)
- `user.last_active`: Timestamp of last activity
- `user.date_joined`: When they joined the team
- `invited_by`: Object with info about who invited them

### Task Fields:
- `id`: Unique task ID
- `name`: Task title
- `description`: Task description (can be empty)
- `status`: Object with status details (status name, color, type: open/closed)
- `date_created`, `date_updated`, `date_closed`, `date_done`: Various timestamps
- `creator`: Object with creator info
- `assignees`: Array of assigned users
- `watchers`: Array of users watching the task
- `priority`: Priority level (can be null)
- `due_date`, `start_date`: Date fields (can be null)
- `time_estimate`: Time estimate in milliseconds (can be null)
- `custom_fields`: Array of custom field values
- `tags`: Array of tags
- `checklists`: Array of checklist items
- `dependencies`: Array of dependent tasks
- `linked_tasks`: Array of linked tasks
- `team_id`: ID of the team
- `url`: Direct link to task in ClickUp
- `list`, `folder`, `space`: Hierarchical location objects