"""
Development playground for testing and experimenting with vex-tm-bridge.
This file is for development purposes only and won't be included in the package.
"""

import time
from vex_tm_bridge import get_bridge_engine
from vex_tm_bridge.base import Competition, Fieldset, FieldsetOverview


def test_basic_monitoring():
    """Test basic fieldset monitoring."""
    engine = get_bridge_engine(low_cpu_usage=True)
    engine.start()

    fieldset = engine.get_fieldset(Competition.V5RC, "Match Field Set #1")
    print("Initial overview:", fieldset.get_overview(), "\n")

    def on_overview_updated(self: Fieldset, overview: FieldsetOverview):
        print(f"Overview updated: {overview}\n")

    fieldset.overview_event.on(on_overview_updated)
    return engine, fieldset


def test_match_control(fieldset: Fieldset):
    """Test match control functions."""
    print("Current state:", fieldset.get_match_state())

    print("Starting match...")
    fieldset.start_match()
    time.sleep(2)

    print("Current state:", fieldset.get_match_state())
    print("Match time:", fieldset.get_match_time())

    # print("Ending match early...")
    # fieldset.end_early()


def main():
    try:
        engine, fieldset = test_basic_monitoring()

        # Uncomment to test match control
        test_match_control(fieldset)

        print("Monitoring for updates (Ctrl+C to stop)...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
        engine.stop()


if __name__ == "__main__":
    main()
