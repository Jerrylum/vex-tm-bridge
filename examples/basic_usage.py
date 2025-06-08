"""Basic usage example of vex-tm-bridge."""

import time
from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition


def main():
    # Create and start the bridge engine
    engine = get_bridge_engine(Competition.V5RC, low_cpu_usage=True)
    engine.start()

    try:
        # Get a fieldset instance
        fieldset = engine.get_fieldset("Match Field Set #1")

        # Print initial overview
        print("Initial overview:")
        print(fieldset.get_overview())

        # Subscribe to overview updates
        def on_overview_updated(self, overview):
            print("\nOverview updated:")
            print(overview)

        fieldset.overview_event.on(on_overview_updated)

        # Keep the script running
        print("\nMonitoring for updates (Ctrl+C to stop)...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping bridge engine...")
        engine.stop()
        print("Done!")


if __name__ == "__main__":
    main()
