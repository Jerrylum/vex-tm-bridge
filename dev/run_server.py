from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition
from vex_tm_bridge.web import create_app

# Create a bridge engine instance
engine = get_bridge_engine(Competition.V5RC, low_cpu_usage=True)

# Create an API application instance
# tm_host_ip is the IP address of the Tournament Manager host machine
# It is not required to enable Local TM API setting in Tournament Manager.
api_server = create_app(tm_host_ip="localhost", bridge_engine=engine)

# Start the application
api_server.start()

# Use uvicorn to serve (api_server.app is the FastAPI instance)
import uvicorn

uvicorn.run(api_server.app, host="0.0.0.0", port=8000)
