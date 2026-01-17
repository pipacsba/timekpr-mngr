# timekpr-mngr

timekpr Manager Architecture  
```
                        ┌─────────────────────┐  
                        │   NiceGUI Frontend  │  
                        │   (UI Pages & Menu) │  
                        └─────────┬───────────┘  
                                  │  
             ┌────────────────────┼───────────────────────┐  
             │                    │                       │  
             │                    │                       │  
   ┌─────────▼─────────┐  ┌───────▼─────────┐   ┌─────────▼─────────┐    
   │ navigation.py     │  │ ui/config_editor│   │ ui/stats_dashboard│    
   │ - Routes          │  │ - Server/user/  │   │ - User stats      │    
   │ - Page wiring     │  │   stats editors │   │ - Dashboard cards │    
   └─────────┬─────────┘  └───────────┬─────┘   └───────────┬───────┘    
             │                        │                     │    
             │                        │                     │    
   ┌─────────▼─────────┐       ┌──────▼─────────┐   ┌───────▼─────────┐    
   │ ui/servers_page.py│       │config_editor.py│   │ dashboard.py    │    
   │ - Server CRUD     │       │ - Parsing logic│   │ - Parsing stats │    
   │ - User CRUD       │       │ - Serialization│   │                 │    
   └─────────┬─────────┘       └───────┬────────┘   └─────────────────┘    
             │                         │    
             │                         │    
   ┌─────────▼─────────┐       ┌───────▼─────────┐    
   │ servers.py        │       │storage.py       │    
   │ - Load/add/delete │       │- Local cache    │    
   │   servers/users   │       │- Pending uploads│    
   │ - Server metadata │       │- /Data dirs     │    
   └─────────┬─────────┘       └───────┬─────────┘    
             │                         │    
             │                         │    
   ┌─────────▼─────────┐       ┌───────▼─────────┐    
   │ ssh_sync.py       │       │ state.py        │    
   │ - Background SSH  │       │ - Global app    │    
   │   sync (SCP)      │       │ state (optional)│    
   │ - Periodic pull   │       └─────────────────┘    
   │ - Pending uploads │    
   └─────────┬─────────┘    
             │    
             ▼    
       Remote Servers    
  ┌─────────────────────┐    
  │ - Server config     │    
  │ - User config files │    
  │ - User stats files  │    
  └─────────────────────┘    
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

## Key Features Shown in Diagram

- Offline-safe: cached files allow UI access if server is down.
- Queued uploads: changes saved locally until server is reachable.
- Modular UI: config editor, server page, dashboard separated.
- Multi-server/multi-user aware: menus and pages dynamically generated.
