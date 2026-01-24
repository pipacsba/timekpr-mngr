#this is under construction as of now yet

# timekpr-mngr

timekpr Manager Architecture  
```
                    ┌───────────────────┐
                    │     main.py       │
                    │ (NiceGUI startup) │
                    └────────┬──────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │                                       │
┌──────────────────┐                    ┌──────────────────┐
│   ssh_sync.py    │                    │ ui/navigation.py │
│ (background job) │                    │ (page registry)  │
└────────┬─────────┘                    └────────┬─────────┘
         │                                       │
         │                       ┌───────────────┼───────────────┐
         │                       │               │               │
┌──────────────────┐   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   servers.py     │   │ servers_page.py  │ │ stats_dashboard  │ │ config_editor    │
│ (domain model)   │   │ (NiceGUI page)   │ │ (NiceGUI page)   │ │ (NiceGUI page)   │
└────────┬─────────┘   └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                      │                    │                    │
         └──────────────┬───────┴───────────┬────────┴──────────┬─────────┘
                        │                   │                   │
                  ┌───────────────────────────────────────────────────┐
                  │                    storage.py                     │
                  │          (persistence / state storage)            │
                  └───────────────────────────────────────────────────┘
  
```
```
main.py
│
├── ssh_sync.py          ← background / sync logic
│   ├── servers.py
│   │   └── storage.py
│   └── storage.py
│
└── ui/navigation.py     ← NiceGUI app entry
    │
    ├── ui/servers_page.py
    │   ├── servers.py
    │   └── storage.py
    │
    ├── ui/stats_dashboard.py
    │   └── storage.py
    │
    └── ui/config_editor.py
        └── storage.py

```

## Data Flow

- User edits configs via ui/config_editor.py → writes to pending_uploads in storage.py.
- SSH sync (ssh_sync.py):
  - Pulls remote server files → caches in /Data/cache/...
  - Pushes pending local changes → uploads to remote server
- Stats dashboard (ui/stats_dashboard.py) reads cached stats and renders human-readable cards.
  - Server management UI (ui/servers_page.py):
  - Add/delete servers
  - Add/delete users
  - Upload SSH keys
- Navigation (navigation.py):
  - Builds menus
  - Registers routes for server/user config & stats pages
- NiceGUI frontend (main.py):
  - Starts the UI
  - Launches SSH background sync thread
