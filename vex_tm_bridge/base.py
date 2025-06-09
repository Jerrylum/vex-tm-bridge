"""Base classes and interfaces for VEX Tournament Manager Bridge.

This module contains the core abstractions and types used throughout the bridge.
It defines the interfaces for interacting with VEX Tournament Manager and the data structures
for representing the state of match fields.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, List, TypeVar, Callable

Self = TypeVar("Self")
EventArg = TypeVar("EventArg")


class Event(ABC, Generic[Self, EventArg]):
    """A generic event system that supports subscribing to and triggering events.

    This class provides a way to register callbacks that will be called when the event
    is triggered. It supports both decorator-style and direct registration of callbacks.

    Type Parameters:
        Self: The type of the object that owns this event
        EventArg: The type of the argument that will be passed to event handlers
    """

    def __init__(self, caller_self: Self) -> None:
        """Initialize the event with its owner object.

        Args:
            caller_self: The object that owns this event. Will be passed as the first
                argument to event handlers.
        """
        self.__listeners: list[Callable[[Self, EventArg], None]] = []
        self.__caller_self = caller_self

    @property
    def on(
        self,
    ) -> Callable[[Callable[[Self, EventArg], None]], Callable[[Self, EventArg], None]]:
        """Decorator for registering event handlers.

        Returns:
            A decorator function that can be used to register event handlers.
        """

        def wrapper(
            func: Callable[[Self, EventArg], None],
        ) -> Callable[[Self, EventArg], None]:
            self.add_listener(func)
            return func

        return wrapper

    def add_listener(self, func: Callable[[Self, EventArg], None]) -> None:
        """Register an event handler.

        Args:
            func: The function to call when the event is triggered.
                Will be called with the owner object and event argument.
        """
        if func in self.__listeners:
            return
        self.__listeners.append(func)

    def remove_listener(self, func: Callable[[Self, EventArg], None]) -> None:
        """Unregister an event handler.

        Args:
            func: The function to remove from the list of event handlers.
        """
        if func not in self.__listeners:
            return
        self.__listeners.remove(func)

    def trigger(self, arg: EventArg) -> None:
        """Trigger the event, calling all registered handlers.

        Args:
            arg: The argument to pass to event handlers.
        """
        for func in self.__listeners:
            func(self.__caller_self, arg)


class Competition(Enum):
    """The type of VEX competition being run."""

    V5RC = ("VEX V5 Robotics Competition",)
    VIQRC = "VEX IQ Robotics Competition"

    def __str__(self) -> str:
        return self.value[0]

    @property
    def name(self) -> str:
        """The full name of the competition."""
        return self.value[0]


class FieldsetAudienceDisplay(Enum):
    """The different display modes available for the audience display."""

    Blank = ("BLANK", "None2", (Competition.V5RC, Competition.VIQRC))
    Logo = ("LOGO", "Logo", (Competition.V5RC, Competition.VIQRC))
    Intro = ("INTRO", "Up Next", (Competition.V5RC, Competition.VIQRC))
    InMatch = ("IN_MATCH", "In-Match", (Competition.V5RC, Competition.VIQRC))
    SavedMatchResults = (
        "RESULTS",
        "Saved Match Results",
        (Competition.V5RC, Competition.VIQRC),
    )
    Schedule = ("SCHEDULE", "Schedule", (Competition.V5RC, Competition.VIQRC))
    Rankings = ("RANKINGS", "Rankings", (Competition.V5RC, Competition.VIQRC))
    SkillsRankings = (
        "SC_RANKINGS",
        "Skills Rankings",
        (Competition.V5RC, Competition.VIQRC),
    )
    AllianceSelection = (
        "ALLIANCE_SELECTION",
        "Alliance Selection",
        (Competition.V5RC,),
    )
    ElimBracket = ("BRACKET", "Elim Bracket", (Competition.V5RC,))
    Slides = ("AWARD", "Award Slides", (Competition.V5RC, Competition.VIQRC))
    Inspection = ("INSPECTION", "Inspection", (Competition.V5RC, Competition.VIQRC))

    def __str__(self) -> str:
        return self.value[1]

    @property
    def name(self) -> str:
        """The internal name used to identify this display mode."""
        return self.value[0]

    @property
    def ui_name(self) -> str:
        """The name shown in the Tournament Manager UI."""
        return self.value[1]

    def available_for(self, competition: Competition) -> bool:
        """Check if this display is available for a given competition type.

        Args:
            competition: The competition type to check.

        Returns:
            True if this display can be used with the given competition type.
        """
        return competition in self.value[2]

    @staticmethod
    def by_name(name: str) -> "FieldsetAudienceDisplay":
        """Get a display mode by its internal name.

        Args:
            name: The internal name of the display mode.

        Returns:
            The corresponding display mode.

        Raises:
            ValueError: If no display mode with the given name exists.
        """
        for display in FieldsetAudienceDisplay:
            if display.value[0] == name:
                return display
        raise ValueError(f"No display found for name: {name}")


class FieldsetQueueSkills(Enum):
    """The types of skills matches that can be queued."""

    AutonomousSkills = ("PROGRAMMING", "Programming")
    DriverSkills = ("DRIVER", "Driver")


class FieldsetState(Enum):
    """The possible states of a match field."""

    Prestart = ("PRESTART", "PRESTART")
    Autonomous = ("AUTONOMOUS", "AUTONOMOUS")
    DriverControl = (
        "DRIVER CONTROL",
        "DRIVER CONTROL",
    )  # although you can only see the word "DRIVER" in the UI
    Pause = ("PAUSED", "PAUSED")
    Disabled = ("DISABLED", "")
    Timeout = ("TIMEOUT", "TIMEOUT")

    def __str__(self) -> str:
        return self.value[0]

    @property
    def name(self) -> str:
        """The internal name of this state."""
        return self.value[0]

    @property
    def ui_name(self) -> str:
        """The name shown in the Tournament Manager UI."""
        return self.value[1]

    @staticmethod
    def by_ui_name(name: str) -> "FieldsetState":
        """Get a state by its UI name.

        Args:
            name: The name shown in the Tournament Manager UI.

        Returns:
            The corresponding state.

        Raises:
            ValueError: If no state with the given UI name exists.
        """
        for state in FieldsetState:
            if state.ui_name == name:
                return state
        raise ValueError(f"No state found for name: {name}")


class FieldsetActiveMatch(Enum):
    """The type of match currently active on a field."""

    NoActiveMatch = "NO ACTIVE MATCH"
    Timeout = "TIMEOUT"
    Match = "MATCH"

    def __str__(self) -> str:
        return self.value

    @property
    def name(self) -> str:
        """The name of this match type."""
        return self.value

    @staticmethod
    def by_name(name: str) -> "FieldsetActiveMatch":
        """Get a match type by its name.

        Args:
            name: The name of the match type.

        Returns:
            The corresponding match type.

        Raises:
            ValueError: If no match type with the given name exists.
        """
        for match_type in FieldsetActiveMatch:
            if match_type.name == name:
                return match_type
        raise ValueError(f"No match type found for name: {name}")


class FieldsetAutonomousBonus(Enum):
    """The possible states of the autonomous bonus."""

    NoBonus = ("NONE", "None")
    Tie = ("TIE", "Tie")
    Red = ("RED", "Red")
    Blue = ("BLUE", "Blue")

    def __str__(self) -> str:
        return self.value[0]

    @property
    def name(self) -> str:
        """The internal name of this bonus state."""
        return self.value[0]

    @property
    def ui_name(self) -> str:
        """The name shown in the Tournament Manager UI."""
        return self.value[1]

    @staticmethod
    def by_name(name: str) -> "FieldsetAutonomousBonus":
        """Get a bonus state by its internal name.

        Args:
            name: The internal name of the bonus state.

        Returns:
            The corresponding bonus state.

        Raises:
            ValueError: If no bonus state with the given name exists.
        """
        for bonus in FieldsetAutonomousBonus:
            if bonus.name == name:
                return bonus
        raise ValueError(f"No bonus found for name: {name}")


class FieldsetOverview:
    """A snapshot of the current state of a match field."""

    def __init__(
        self,
        audience_display: FieldsetAudienceDisplay,
        match_timer_content: str | None,
        match_time: int,
        prestart_time: int,
        match_state: FieldsetState,
        current_field_id: int | None,
        match_on_field: str | None,
        saved_match_results: str | None,
        autonomous_bonus: FieldsetAutonomousBonus,
        play_sounds: bool,
        show_results_automatically: bool,
        active_match: FieldsetActiveMatch,
    ) -> None:
        """Initialize a new field overview."""
        self.audience_display = audience_display
        self.match_timer_content = match_timer_content
        self.match_time = match_time
        self.prestart_time = prestart_time
        self.match_state = match_state
        self.current_field_id = current_field_id
        self.match_on_field = match_on_field
        self.saved_match_results = saved_match_results
        self.autonomous_bonus = autonomous_bonus
        self.play_sounds = play_sounds
        self.show_results_automatically = show_results_automatically
        self.active_match = active_match

    def __str__(self) -> str:
        return f"FieldsetOverview(audience_display={self.audience_display}, match_timer_content={self.match_timer_content}, match_time={self.match_time}, prestart_time={self.prestart_time}, match_state={self.match_state}, current_field_id={self.current_field_id}, match_on_field={self.match_on_field}, saved_match_results={self.saved_match_results}, autonomous_bonus={self.autonomous_bonus}, play_sounds={self.play_sounds}, show_results_automatically={self.show_results_automatically}, match_on_field={self.match_on_field}, active_match={self.active_match})"

    def __hash__(self) -> int:
        return hash(
            (
                self.audience_display,
                self.match_timer_content,
                self.match_time,
                self.prestart_time,
                self.match_state,
                self.current_field_id,
                self.match_on_field,
                self.saved_match_results,
                self.autonomous_bonus,
                self.play_sounds,
                self.show_results_automatically,
                self.active_match,
            )
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FieldsetOverview):
            return False
        return self.__hash__() == other.__hash__()


class Team:
    """A team in the tournament."""

    def __init__(self, no: str, name: str, location: str, school: str) -> None:
        self.no = no
        self.name = name
        self.location = location
        self.school = school

    def __str__(self) -> str:
        return f"Team(no={self.no}, name={self.name}, location={self.location}, school={self.school})"


class Match(ABC):
    """A match in the tournament."""

    def __init__(self, id: str) -> None:
        self.id = id


class MatchV5RC(Match):
    """A match in the tournament."""

    def __init__(self, id: str, red_team: List[str], blue_team: List[str], red_score: int, blue_score: int) -> None:
        super().__init__(id)
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_score = red_score
        self.blue_score = blue_score

    def __str__(self) -> str:
        return f"MatchV5RC(id={self.id}, red_team={self.red_team}, blue_team={self.blue_team}, red_score={self.red_score}, blue_score={self.blue_score})"


class MatchVIQRC(Match):
    """A match in the tournament."""

    def __init__(self, id: str, team_1: str, team_2: str, score: float | None) -> None:
        super().__init__(id)
        self.team_1 = team_1
        self.team_2 = team_2
        self.score = score

    def __str__(self) -> str:
        return f"MatchVIQRC(id={self.id}, team_1={self.team_1}, team_2={self.team_2}, score={self.score})"


class Ranking(ABC):
    """A ranking in the tournament."""

    def __init__(self, rank: int, team_no: str) -> None:
        self.rank = rank
        self.team_no = team_no


class RankingV5RC(Ranking):
    """A ranking in the tournament."""

    def __init__(
        self,
        rank: int,
        team_no: str,
        average_wps: float,
        average_aps: float,
        average_sps: float,
        wins: int,
        losses: int,
        ties: int,
    ) -> None:
        super().__init__(rank, team_no)
        self.average_wps = average_wps
        self.average_aps = average_aps
        self.average_sps = average_sps
        self.wins = wins
        self.losses = losses
        self.ties = ties

    def __str__(self) -> str:
        return f"RankingV5RC(rank={self.rank}, team_no={self.team_no}, average_wps={self.average_wps}, average_aps={self.average_aps}, average_sps={self.average_sps}, wins={self.wins}, losses={self.losses}, ties={self.ties})"


class RankingVIQRC(Ranking):
    """A ranking in the tournament."""

    def __init__(self, rank: int, team_no: str, matches_played: int, average_score: float) -> None:
        super().__init__(rank, team_no)
        self.matches_played = matches_played
        self.average_score = average_score

    def __str__(self) -> str:
        return f"RankingVIQRC(rank={self.rank}, team_no={self.team_no}, matches_played={self.matches_played}, average_score={self.average_score})"


class SkillsRanking:
    """A skills ranking in the tournament."""

    def __init__(
        self,
        rank: int,
        team_no: str,
        team_name: str,
        total_score: float,
        prog_high_score: float,
        prog_attempts: int,
        driver_high_score: float,
        driver_attempts: int,
    ) -> None:
        self.rank = rank
        self.team_no = team_no
        self.team_name = team_name
        self.total_score = total_score
        self.prog_high_score = prog_high_score
        self.prog_attempts = prog_attempts
        self.driver_high_score = driver_high_score
        self.driver_attempts = driver_attempts

    def __str__(self) -> str:
        return f"SkillsRanking(rank={self.rank}, team_no={self.team_no}, team_name={self.team_name}, total_score={self.total_score}, prog_high_score={self.prog_high_score}, prog_attempts={self.prog_attempts}, driver_high_score={self.driver_high_score}, driver_attempts={self.driver_attempts})"


class Fieldset(ABC):
    """Interface for controlling a match field in Tournament Manager.

    This class provides methods to monitor and control a VEX Tournament Manager match field.
    It uses pywinauto to interact with the UI elements of the Tournament Manager software.

    The fieldset provides functionality to:
    - Monitor match state and timing
    - Control match flow (start, stop, abort)
    - Configure display settings
    - Set field parameters
    - Handle autonomous bonus scoring
    - Manage sound and results display settings

    Each fieldset instance is associated with a specific window in Tournament Manager
    and maintains its own state. The fieldset will automatically reconnect if the
    window is temporarily lost.

    The implementation uses pywinauto's control wrappers to interact with UI elements:
    - Buttons for match control and display settings
    - Static text fields for state and timing information
    - Combo boxes for field selection
    - Checkboxes for sound and results settings
    """

    def __init__(self, competition: Competition) -> None:
        """Initialize a new fieldset.

        Args:
            competition: The type of competition this field is being used for.
        """
        self.overview_updated_event = FieldsetOverviewUpdatedEvent(self)
        self.competition = competition

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if this fieldset is connected to Tournament Manager.

        The fieldset is considered connected if it has a valid window handle and
        can interact with the Tournament Manager UI.

        Returns:
            True if the fieldset is connected and can be controlled.
        """
        ...

    @abstractmethod
    def get_fieldset_title(self) -> str:
        """Get the title of this fieldset's window.

        This title is used to identify and reconnect to the window if the
        connection is lost.

        Returns:
            The window title used to identify this fieldset.
        """
        ...

    @abstractmethod
    def get_overview(self) -> FieldsetOverview:
        """Get a snapshot of the current field state.

        This method retrieves all current state from the UI, including:
        - Display mode
        - Match timing
        - Field state
        - Match information
        - Settings

        Returns:
            An overview containing all current field state.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def start_match(self) -> None:
        """Start or resume the match.

        This method will:
        - Start a new match if in disabled state
        - Resume a paused match if in paused state

        Raises:
            ValueError: If the match cannot be started in its current state
                (e.g. already running or ended).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def end_early(self) -> None:
        """End the match early.

        Raises:
            ValueError: If the match cannot be ended in its current state
                (e.g. already ended or during prestart).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def abort_match(self) -> None:
        """Abort the match.

        Raises:
            ValueError: If the match cannot be aborted in its current state
                (e.g. paused).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def reset_timer(self) -> None:
        """Reset the match timer.

        Raises:
            ValueError: If the timer cannot be reset in its current state
                (e.g. match not ended).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def set_audience_display(self, display: FieldsetAudienceDisplay) -> None:
        """Set the audience display mode.

        Args:
            display: The display mode to switch to.

        Raises:
            ValueError: If the display mode is not available for this competition.
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_audience_display(self) -> FieldsetAudienceDisplay:
        """Get the current audience display mode.

        Returns:
            The current display mode.

        Raises:
            ValueError: If no display mode is currently selected.
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_match_time(self) -> int:
        """Get the current match time in seconds.

        Returns:
            The current match time, or 0 if no match is running.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_prestart_time(self) -> int:
        """Get the current prestart time in seconds.

        Returns:
            The current prestart time, or 0 if not in prestart.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_match_timer_content(self) -> str | None:
        """Get the raw match timer content from the UI.

        Returns:
            The timer content as shown in the UI, or None if not available.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_match_state(self) -> FieldsetState:
        """Get the current match state.

        Returns:
            The current state of the match.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def set_current_field_id(self, field_id: int | str) -> None:
        """Set the current field ID.

        Args:
            field_id: The field ID to select.

        Raises:
            ValueError: If the field ID cannot be set in the current state
                (e.g. match running, paused, or ended).
            IndexError: If the field ID is not valid.
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_current_field_id(self) -> int | None:
        """Get the current field ID.

        Returns:
            The current field ID, or None if no field is selected.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_match_on_field(self) -> str | None:
        """Get the match currently on the field.

        Returns:
            The match identifier, or None if no match is on the field.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_saved_match_results(self) -> str | None:
        """Get the saved match results.

        Returns:
            The match results, or None if no results are saved.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def set_autonomous_bonus(self, bonus: FieldsetAutonomousBonus) -> None:
        """Set the autonomous bonus.

        Args:
            bonus: The bonus state to set.

        Raises:
            ValueError: If autonomous bonus is not available in the current state
                (e.g. wrong competition type or during timeout).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_autonomous_bonus(self) -> FieldsetAutonomousBonus:
        """Get the current autonomous bonus state.

        Returns:
            The current bonus state.

        Raises:
            ValueError: If autonomous bonus is not available in the current state
                (e.g. wrong competition type or during timeout).
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def set_play_sounds(self, play_sounds: bool) -> None:
        """Enable or disable sound effects.

        Args:
            play_sounds: Whether to play sound effects.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def is_play_sounds(self) -> bool:
        """Check if sound effects are enabled.

        Returns:
            True if sound effects are enabled.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def set_show_results_automatically(self, show_results_automatically: bool) -> None:
        """Enable or disable automatic results display.

        Args:
            show_results_automatically: Whether to show results automatically.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def is_show_results_automatically(self) -> bool:
        """Check if automatic results display is enabled.

        Returns:
            True if results are shown automatically.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...

    @abstractmethod
    def get_active_match(self) -> FieldsetActiveMatch:
        """Get the type of match currently active.

        Returns:
            The type of match currently on the field.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        ...


class FieldsetOverviewUpdatedEvent(Event[Fieldset, FieldsetOverview]):
    """Event that is triggered when the fieldset overview is updated."""

    def __init__(self, caller_self: Fieldset) -> None:
        """Initialize a new overview event.

        Args:
            caller_self: The fieldset that owns this event.
        """
        super().__init__(caller_self)


M = TypeVar("M", bound=Match)
R = TypeVar("R", bound=Ranking)
C = TypeVar("C", bound=Competition)


class TournamentManagerWebServer(ABC, Generic[M, R]):
    """Interface for interacting with the Tournament Manager web server.

    Type Parameters:
        Match: The type of match (MatchV5RC or MatchVIQRC)
        Ranking: The type of ranking (RankingV5RC or RankingVIQRC)
    """

    def __init__(self, tm_host_ip: str, competition: Competition) -> None:
        """Initialize a new web server interface.

        Args:
            tm_host_ip: The IP address of the Tournament Manager web server
            competition: The type of competition (V5RC or VIQRC)
        """
        self.tm_host_ip = tm_host_ip
        self.competition = competition

    @abstractmethod
    def get_teams(self, division_no: int) -> List[Team]:
        """Get the list of teams in a division.

        Args:
            division_no: The division number to get teams from

        Returns:
            A list of teams in the division

        Raises:
            Exception: If there is an error fetching the teams
        """
        ...

    @abstractmethod
    def get_matches(self, division_no: int) -> List[M]:
        """Get the list of matches in a division.

        Args:
            division_no: The division number to get matches from

        Returns:
            A list of matches in the division. For V5RC competitions, returns List[MatchV5RC].
            For VIQRC competitions, returns List[MatchVIQRC].

        Raises:
            Exception: If there is an error fetching the matches
        """
        ...

    @abstractmethod
    def get_rankings(self, division_no: int) -> List[R]:
        """Get the rankings in a division.

        Args:
            division_no: The division number to get rankings from

        Returns:
            A list of rankings in the division. For V5RC competitions, returns List[RankingV5RC].
            For VIQRC competitions, returns List[RankingVIQRC].

        Raises:
            Exception: If there is an error fetching the rankings
        """
        ...

    @abstractmethod
    def get_skills_rankings(self) -> List[SkillsRanking]:
        """Get the skills rankings.

        Returns:
            A list of skills rankings

        Raises:
            Exception: If there is an error fetching the skills rankings
        """
        ...


class BridgeEngine(ABC):
    """Abstract base class for the bridge engine that monitors multiple fieldsets."""

    def __init__(self, competition: Competition, low_cpu_usage: bool) -> None:
        """Initialize a new bridge engine.

        Args:
            competition: The competition type (V5RC or VIQRC)
            low_cpu_usage: Whether to use low CPU mode. In low CPU mode, the bridge
                engine will use cached values 90% of the time and only do a full
                refresh every 10th iteration (every 100ms).
        """
        self.competition = competition
        self.low_cpu_usage = low_cpu_usage

    @abstractmethod
    def start(self) -> None:
        """Start the bridge engine monitoring."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the bridge engine monitoring."""
        pass

    @abstractmethod
    def get_fieldset(self, title: str) -> Fieldset:
        """Get a fieldset by its window title. Creates one if it doesn't exist.

        Args:
            title: The window title of the fieldset

        Returns:
            The fieldset instance

        Raises:
            WindowNotFoundError: If the window cannot be found
            Exception: If the bridge engine is not running
        """
        pass

    @abstractmethod
    def get_web_server(self, tm_host_ip: str) -> "TournamentManagerWebServer":
        """Get a web server instance for interacting with Tournament Manager web interface.

        Args:
            tm_host_ip: The IP address of the Tournament Manager web server

        Returns:
            A web server instance typed based on the competition type.
            For V5RC: TournamentManagerWebServer[MatchV5RC, RankingV5RC]
            For VIQRC: TournamentManagerWebServer[MatchVIQRC, RankingVIQRC]
        """
        pass


class BridgeEngineV5RC(BridgeEngine, ABC):
    """V5RC-specific bridge engine implementation."""

    def __init__(self, low_cpu_usage: bool) -> None:
        super().__init__(Competition.V5RC, low_cpu_usage)

    @abstractmethod
    def get_web_server(self, tm_host_ip: str) -> TournamentManagerWebServer[MatchV5RC, RankingV5RC]:
        """Get a web server instance for interacting with Tournament Manager web interface.

        Args:
            tm_host_ip: The IP address of the Tournament Manager web server

        Returns:
            A web server instance typed based on the competition type.
            TournamentManagerWebServer[MatchV5RC, RankingV5RC]
        """
        pass


class BridgeEngineVIQRC(BridgeEngine, ABC):
    """VIQRC-specific bridge engine implementation."""

    def __init__(self, low_cpu_usage: bool) -> None:
        super().__init__(Competition.VIQRC, low_cpu_usage)

    @abstractmethod
    def get_web_server(self, tm_host_ip: str) -> TournamentManagerWebServer[MatchVIQRC, RankingVIQRC]:
        """Get a web server instance for interacting with Tournament Manager web interface.

        Args:
            tm_host_ip: The IP address of the Tournament Manager web server
        """
        pass
