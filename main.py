from fastapi import FastAPI
from nicegui import ui
from nicegui.fastapi import configure as configure_nicegui

# Create a FastAPI app
app = FastAPI()

# Configure NiceGUI with relative static paths
configure_nicegui(
    app,
    static_url_path="nicegui-static",  # key change
    title="HA Addon NiceGUI",
)

# Now define your NiceGUI UI
@ui.page('/')
def main_page():
    ui.label("Hello HA NiceGUI ingress!")

# Run the NiceGUI app on host/port like before
ui.run_with(app, host="0.0.0.0", port=5002, reload=False)
