# timekpr-mngr

timekpr-mngr is a NiceGUI-based management and monitoring tool for Timekpr servers.
It synchronizes server configs over SSH, collects user usage statistics, and exposes server
and user data to Home Assistant via MQTT Auto Discovery.

The design intentionally avoids heavy dependencies (databases, rsync requirements on servers),
while still integrating cleanly into a modern HA setup.

# timekpr Manager Architecture  
```
                    ┌───────────────────┐
                    │     main.py       │
                    │ (NiceGUI startup) │
                    └────────┬──────────┘
                             │
         ┌───────────────────┴──────────────────────────┐
         │                                              │
┌──────────────────┐                          ┌────────────────────┐
│   ssh_sync.py    │                          │  ui/navigation.py  │
│ (background job) │                          │ (page registry)    │
└────────┬─────────┘                          └────────┬───────────┘
         │                                              │
         │                    ┌─────────────────────────┼───────────────┐
         │                    │                         │               │
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   servers.py     │ │ servers_page.py  │ │ stats_dashboard  │ │ config_editor    │
│ (domain model)   │ │ (NiceGUI page)   │ │ (NiceGUI page)   │ │ (NiceGUI page)   │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │                    │
         └──────────────┬─────┴───────────┬────────┴──────────┬─────────┘
                        │                 │                   │
                  ┌───────────────────────────────────────────────────┐
                  │                    storage.py                     │
                  │          (shared state & persistence)             │
                  └───────────────────────────────────────────────────┘
                                │
                                │
                  ┌────────────────────────────────────────────────────┐
                  │                stats_history.py                    │
                  │      (rolling per-user daily statistics)           │
                  └────────────────────────────────────────────────────┘
                                │
                                │
                  ┌───────────────────────────────────────────────────┐
                  │                    MQTT / HA                      │
                  │  - server online list                             │
                  │  - per-server binary sensors                      │
                  │  - user daily usage sensors                       │
                  └───────────────────────────────────────────────────┘
```

## Data Flow
### Configuration
- User edits configs via ui/config_editor.py
- Changes are written to pending_uploads/
- No immediate server-side changes are required  

### SSH Synchronization (ssh_sync.py)
Runs every 3 minutes or on manual trigger:
- Checks server reachability
- Pulls Timekpr files (users, stats)
- Uploads pending local changes if server is online
- Detects online servers
- Parses user *.stat files

## User Statistics Handling
- Stats are read from user.stat files on the servers
  - Important fields:
    - TIME_SPENT_DAY
    - PLAYTIME_SPENT_DAY
    - LAST_CHECKED

### Freshness check
Stats are only published if:
 - LAST_CHECKED.date() == today  
This avoids publishing stale usage when users haven’t logged in that day.

### Storage
- stats_history.py maintains a rolling history (e.g. last 30 days)
- Stored locally as JSON (simple, inspectable, backup-friendly)
- No database required

## MQTT & Home Assistant Integration
### Server Online State

A single topic is published:
```
timekpr/servers/online
Payload:
{"servers": ["server1", "server3"]}
```
From this, HA auto-discovers:
- One binary_sensor per server
- All sensors derive state from the same topic using value_template

Example template:
```
{{ 'server1' in value_json.servers }}
```
## Home Assistant Auto Discovery

Uses MQTT discovery
- Entities are retained
- Device is grouped under a single timekpr-mngr device
- QoS configurable (default: 1)

Supported entity types:
- binary_sensor → server online status
- sensor → daily user usage (TIME_SPENT_DAY / PLAYTIME_SPENT_DAY)

## Background Execution Model

- SSH sync runs in a dedicated thread started via FastAPI lifespan
- Supports:
  - Periodic execution
  - External trigger via threading.Event
- Clean shutdown on app exit

# Dependencies

Key dependencies:
- nicegui
- fastapi
- paramiko
- paho-mqtt
- jinja2
(See requirements.txt)
