"""
Web API server for VEX Tournament Manager Bridge.

This module provides a RESTful API and Server-Sent Events interface for
interacting with VEX Tournament Manager through the bridge.
"""

import asyncio
import json
import threading
import time
from typing import Dict, List, Optional, Union

import click
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from starlette.responses import JSONResponse

from .base import (
    BridgeEngine,
    Competition,
    Fieldset,
    FieldsetOverview,
    FieldsetAudienceDisplay,
    FieldsetAutonomousBonus,
    FieldsetState,
    FieldsetActiveMatch,
    FieldsetQueueSkills,
    Team,
    MatchV5RC,
    MatchVIQRC,
    RankingV5RC,
    RankingVIQRC,
    SkillsRanking,
)
from .impl import get_bridge_engine


class APIServer:
    """FastAPI server for VEX Tournament Manager Bridge."""

    def __init__(self, tm_host_ip: str, bridge_engine: BridgeEngine):
        """Initialize the API server.

        Args:
            tm_host_ip: IP address of Tournament Manager web server
            competition: Competition type (V5RC or VIQRC)
        """
        self.tm_host_ip = tm_host_ip
        self.engine = bridge_engine
        self.competition = bridge_engine.competition
        self.app = FastAPI(
            title="VEX Tournament Manager Bridge API",
            description="REST API for interacting with VEX Tournament Manager",
            version="0.1.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Initialize web server handler
        self.web_server = self.engine.get_web_server(tm_host_ip)

        # Active fieldsets and their SSE connections
        self.fieldsets: Dict[str, Fieldset] = {}
        self.sse_connections: Dict[str, List[asyncio.Queue]] = {}

        self._setup_routes()

    def _setup_routes(self):
        """Set up all API routes."""

        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "ok", "competition": self.competition.name}

        # Teams endpoint
        @self.app.get("/api/teams/{division_id}")
        async def get_teams(division_id: int = Path(..., description="Division ID")):
            try:
                teams = self.web_server.get_teams(division_id)
                return [team.__dict__ for team in teams]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Matches endpoint
        @self.app.get("/api/matches/{division_id}")
        async def get_matches(division_id: int = Path(..., description="Division ID")):
            try:
                matches = self.web_server.get_matches(division_id)
                return [match.__dict__ for match in matches]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Rankings endpoint
        @self.app.get("/api/rankings/{division_id}")
        async def get_rankings(division_id: int = Path(..., description="Division ID")):
            try:
                rankings = self.web_server.get_rankings(division_id)
                return [ranking.__dict__ for ranking in rankings]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Skills rankings endpoint
        @self.app.get("/api/skills")
        async def get_skills_rankings():
            try:
                skills = self.web_server.get_skills_rankings()
                return [skill.__dict__ for skill in skills]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Fieldset endpoints
        @self.app.get("/api/fieldset/{fieldset_title}")
        async def get_fieldset_overview(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                overview = fieldset.get_overview()
                return self._serialize_overview(overview)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/start")
        async def start_match(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.start_match()
                return {"status": "success", "message": "Match started"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/end-early")
        async def end_match_early(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.end_early()
                return {"status": "success", "message": "Match ended early"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/abort")
        async def abort_match(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.abort_match()
                return {"status": "success", "message": "Match aborted"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/reset")
        async def reset_timer(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.reset_timer()
                return {"status": "success", "message": "Timer reset"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Audience display endpoints
        @self.app.get("/api/fieldset/{fieldset_title}/display")
        async def get_audience_display(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                display = fieldset.get_audience_display()
                return {"display": display.name}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/display")
        async def set_audience_display(
            fieldset_title: str = Path(..., description="Fieldset window title"),
            display: str = Query(..., description="Display mode name"),
        ):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                display_mode = FieldsetAudienceDisplay.by_name(display)
                fieldset.set_audience_display(display_mode)
                return {"status": "success", "message": f"Display set to {display}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Field ID endpoints
        @self.app.get("/api/fieldset/{fieldset_title}/field-id")
        async def get_current_field_id(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                field_id = fieldset.get_current_field_id()
                return {"field_id": field_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/field-id")
        async def set_current_field_id(
            fieldset_title: str = Path(..., description="Fieldset window title"),
            field_id: Union[int, str] = Query(..., description="Field ID to set"),
        ):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.set_current_field_id(field_id)
                return {"status": "success", "message": f"Field ID set to {field_id}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Autonomous bonus endpoints (V5RC only)
        @self.app.get("/api/fieldset/{fieldset_title}/autonomous-bonus")
        async def get_autonomous_bonus(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                if self.competition != Competition.V5RC:
                    raise HTTPException(status_code=400, detail="Autonomous bonus only available for V5RC")
                fieldset = self._get_fieldset(fieldset_title)
                bonus = fieldset.get_autonomous_bonus()
                return {"bonus": bonus.name}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/autonomous-bonus")
        async def set_autonomous_bonus(
            fieldset_title: str = Path(..., description="Fieldset window title"),
            bonus: str = Query(..., description="Bonus state name"),
        ):
            try:
                if self.competition != Competition.V5RC:
                    raise HTTPException(status_code=400, detail="Autonomous bonus only available for V5RC")
                fieldset = self._get_fieldset(fieldset_title)
                bonus_state = FieldsetAutonomousBonus.by_name(bonus)
                fieldset.set_autonomous_bonus(bonus_state)
                return {"status": "success", "message": f"Autonomous bonus set to {bonus}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Sound settings endpoints
        @self.app.get("/api/fieldset/{fieldset_title}/play-sounds")
        async def get_play_sounds(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                play_sounds = fieldset.is_play_sounds()
                return {"play_sounds": play_sounds}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/play-sounds")
        async def set_play_sounds(
            fieldset_title: str = Path(..., description="Fieldset window title"),
            play_sounds: bool = Query(..., description="Whether to play sounds"),
        ):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.set_play_sounds(play_sounds)
                return {"status": "success", "message": f"Play sounds set to {play_sounds}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Auto results settings endpoints
        @self.app.get("/api/fieldset/{fieldset_title}/auto-results")
        async def get_show_results_automatically(fieldset_title: str = Path(..., description="Fieldset window title")):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                auto_results = fieldset.is_show_results_automatically()
                return {"auto_results": auto_results}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/fieldset/{fieldset_title}/auto-results")
        async def set_show_results_automatically(
            fieldset_title: str = Path(..., description="Fieldset window title"),
            auto_results: bool = Query(..., description="Whether to show results automatically"),
        ):
            try:
                fieldset = self._get_fieldset(fieldset_title)
                fieldset.set_show_results_automatically(auto_results)
                return {"status": "success", "message": f"Auto results set to {auto_results}"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Server-Sent Events endpoint for fieldset updates
        @self.app.get("/api/fieldset/{fieldset_title}/events")
        async def fieldset_events(fieldset_title: str = Path(..., description="Fieldset window title")):
            return EventSourceResponse(self._event_generator(fieldset_title))

    def _get_fieldset(self, fieldset_title: str) -> Fieldset:
        """Get or create a fieldset instance."""
        if fieldset_title not in self.fieldsets:
            fieldset = self.engine.get_fieldset(fieldset_title)
            self.fieldsets[fieldset_title] = fieldset
            self.sse_connections[fieldset_title] = []

            # Set up event handler for overview updates
            def on_overview_updated(fs: Fieldset, overview: FieldsetOverview):
                self._broadcast_update(fieldset_title, overview)

            fieldset.overview_updated_event.add_listener(on_overview_updated)

        return self.fieldsets[fieldset_title]

    def _serialize_overview(self, overview: FieldsetOverview) -> dict:
        """Serialize a FieldsetOverview to a dictionary."""
        return {
            "audience_display": overview.audience_display.name,
            "match_timer_content": overview.match_timer_content,
            "match_time": overview.match_time,
            "prestart_time": overview.prestart_time,
            "match_state": overview.match_state.name,
            "current_field_id": overview.current_field_id,
            "match_on_field": overview.match_on_field,
            "saved_match_results": overview.saved_match_results,
            "autonomous_bonus": overview.autonomous_bonus.name,
            "play_sounds": overview.play_sounds,
            "show_results_automatically": overview.show_results_automatically,
            "active_match": overview.active_match.name,
        }

    def _broadcast_update(self, fieldset_title: str, overview: FieldsetOverview):
        """Broadcast an update to all SSE connections for a fieldset."""
        if fieldset_title in self.sse_connections:
            serialized = self._serialize_overview(overview)
            for queue in self.sse_connections[fieldset_title]:
                try:
                    queue.put_nowait(serialized)
                except asyncio.QueueFull:
                    # Skip if queue is full
                    pass

    async def _event_generator(self, fieldset_title: str):
        """Generate Server-Sent Events for a fieldset."""
        queue = asyncio.Queue(maxsize=100)

        # Add this connection to the list
        if fieldset_title not in self.sse_connections:
            self.sse_connections[fieldset_title] = []
        self.sse_connections[fieldset_title].append(queue)

        # Get the fieldset to ensure it's being monitored
        fieldset = self._get_fieldset(fieldset_title)

        try:
            # Send initial state
            overview = fieldset.get_overview()
            yield {"event": "overview", "data": json.dumps(self._serialize_overview(overview))}

            # Stream updates
            while True:
                try:
                    # Wait for updates with timeout
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "overview", "data": json.dumps(update)}
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": ""}
        finally:
            # Remove this connection from the list
            if fieldset_title in self.sse_connections:
                try:
                    self.sse_connections[fieldset_title].remove(queue)
                except ValueError:
                    pass

    def start(self):
        """Start the bridge engine."""
        self.engine.start()

    def stop(self):
        """Stop the bridge engine."""
        self.engine.stop()


def create_app(tm_host_ip: str, bridge_engine: BridgeEngine) -> APIServer:
    """Create and configure the API server.

    Args:
        tm_host_ip: IP address of Tournament Manager web server
        competition: Competition type (V5RC or VIQRC)

    Returns:
        Configured API server instance
    """
    return APIServer(tm_host_ip, bridge_engine)


@click.command()
@click.option("--tm-host-ip", default="localhost", help="Tournament Manager host IP address")
@click.option("--competition", type=click.Choice(["V5RC", "VIQRC"]), default="V5RC", help="Competition type")
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to run the API server on")
def main(tm_host_ip: str, competition: str, host: str, port: int):
    """Start the VEX Tournament Manager Bridge API server."""
    comp = Competition.V5RC if competition == "V5RC" else Competition.VIQRC

    # Create and start the API server
    api_server = create_app(tm_host_ip, get_bridge_engine(comp, low_cpu_usage=True))
    api_server.start()

    try:
        print(f"Starting VEX TM Bridge API server on {host}:{port}")
        print(f"Competition: {comp.name}")
        print(f"Tournament Manager: {tm_host_ip}")
        print(f"API Documentation: http://{host}:{port}/docs")

        uvicorn.run(api_server.app, host=host, port=port)
    finally:
        api_server.stop()
