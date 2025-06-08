"""Implementation of the VEX Tournament Manager Bridge.

This module contains the concrete implementation of the bridge interfaces using pywinauto
to interact with the VEX Tournament Manager software. It provides functionality to monitor
and control match fields through the Tournament Manager UI.
"""

from abc import ABC
import threading
import time
from typing import Dict, List, Union, Optional, overload, Literal

import requests
from bs4 import BeautifulSoup, Tag
from .base import (
    BridgeEngine,
    BridgeEngineV5RC,
    BridgeEngineVIQRC,
    Fieldset,
    FieldsetActiveMatch,
    FieldsetOverview,
    FieldsetState,
    FieldsetAudienceDisplay,
    Competition,
    FieldsetQueueSkills,
    FieldsetAutonomousBonus,
    MatchV5RC,
    MatchVIQRC,
    RankingV5RC,
    RankingVIQRC,
    SkillsRanking,
    Team,
    TournamentManagerWebServer,
    M,
    R,
    C,
)
from pywinauto.application import WindowSpecification
from pywinauto import Application, findwindows
import pywinauto.base_wrapper
from pywinauto.controls.win32_controls import ButtonWrapper, ComboBoxWrapper
from pywinauto.controls.hwndwrapper import HwndWrapper

# Type alias for pywinauto control wrappers
ControlWrapper = Union[ButtonWrapper, ComboBoxWrapper, HwndWrapper]


def impl_start_match(
    start_match_button: ButtonWrapper,
    resume_match_button: ButtonWrapper,
    match_state_control: HwndWrapper,
) -> None:
    """Start or resume a match.

    This function handles both starting a new match and resuming a paused match.
    It checks the current match state to determine the appropriate action.

    Args:
        start_match_button: The "Start Match" button control
        resume_match_button: The "Resume Match" button control
        match_state_control: The match state display control

    Raises:
        ValueError: If the match cannot be started in its current state
    """
    try:
        current_field_state = impl_get_match_state(match_state_control)
        if current_field_state == FieldsetState.Pause:
            resume_match_button.click()
        elif current_field_state == FieldsetState.Disabled and resume_match_button.is_enabled():
            # XXX: The tournament manager might not be able to start the match if some edge cases.
            # Use reset timer to ensure the match is in a valid state.
            start_match_button.click()
        else:
            # IMPORTANT: Do not click the button if the match is already started or ended.
            raise ValueError(
                f"Unable to start match. The match might be started already or ended (need to click Reset Timer)."
            )
    except Exception as e:
        raise ValueError(f"Error starting match: {e}")


def impl_end_early(end_early_button: ButtonWrapper) -> None:
    """End the current match early.

    Args:
        end_early_button: The "End Early" button control

    Raises:
        ValueError: If the match cannot be ended in its current state
    """
    try:
        end_early_button.click()
    except pywinauto.base_wrapper.ElementNotEnabled:
        raise ValueError(f"Unable to end early. The match might be ended already or during a prestart.")
    except Exception as e:
        raise ValueError(f"Error ending early: {e}")


def impl_abort_match(abort_match_button: ButtonWrapper) -> None:
    """Abort the current match.

    Args:
        abort_match_button: The "Abort Match" button control

    Raises:
        ValueError: If the match cannot be aborted in its current state
    """
    try:
        abort_match_button.click()
    except pywinauto.base_wrapper.ElementNotEnabled:
        raise ValueError(f"Unable to abort match. The match might be paused.")
    except Exception as e:
        raise ValueError(f"Error aborting match: {e}")


def impl_reset_timer(reset_timer_button: ButtonWrapper) -> None:
    """Reset the match timer.

    Args:
        reset_timer_button: The "Reset Timer" button control

    Raises:
        ValueError: If the timer cannot be reset in its current state
    """
    try:
        reset_timer_button.click()
    except pywinauto.base_wrapper.ElementNotEnabled:
        raise ValueError(f"Unable to reset timer. The match is not ended.")
    except Exception as e:
        raise ValueError(f"Error resetting timer: {e}")


def impl_queue_previous_match(queue_previous_match_button: ButtonWrapper) -> None:
    """Queue the previous match.

    Args:
        queue_previous_match_button: The "Queue Previous Match" button control

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("Not implemented")


def impl_queue_next_match(queue_next_match_button: ButtonWrapper) -> None:
    """Queue the next match.

    Args:
        queue_next_match_button: The "Queue Next Match" button control

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("Not implemented")


def impl_queue_skills(skills_button: ButtonWrapper, skills: FieldsetQueueSkills) -> None:
    """Queue a skills match.

    Args:
        skills_button: The skills button control
        skills: The type of skills match to queue

    Raises:
        NotImplementedError: This function is not yet implemented
    """
    raise NotImplementedError("Not implemented")


def impl_set_audience_display(
    display_button: Dict[FieldsetAudienceDisplay, ButtonWrapper],
    display: FieldsetAudienceDisplay,
    competition: Competition,
) -> None:
    """Set the audience display mode.

    Args:
        display_button: Dictionary mapping display modes to their button controls
        display: The display mode to switch to
        competition: The current competition type

    Raises:
        ValueError: If the display mode is not available for this competition
    """
    if not display.available_for(competition):
        raise ValueError(f"Display {display} is not available for {competition}")
    display_button[display].click()


def impl_get_audience_display(
    display_buttons: Dict[FieldsetAudienceDisplay, ButtonWrapper],
    competition: Competition,
) -> FieldsetAudienceDisplay:
    """Get the current audience display mode.

    Args:
        display_buttons: Dictionary mapping display modes to their button controls
        competition: The current competition type

    Returns:
        The current display mode

    Raises:
        ValueError: If no display mode is currently selected
    """
    for display, button in display_buttons.items():
        if display.available_for(competition) and button.get_check_state():
            return display
    raise ValueError("No display found")


def impl_get_audience_display_lazy(
    display_buttons: Dict[FieldsetAudienceDisplay, ButtonWrapper],
    competition: Competition,
    last_display: FieldsetAudienceDisplay,
) -> FieldsetAudienceDisplay:
    """Get the current audience display mode, using a cached value if possible.

    This is an optimization that checks if the last known display mode is still
    active before doing a full scan of all display buttons.

    Args:
        display_buttons: Dictionary mapping display modes to their button controls
        competition: The current competition type
        last_display: The last known display mode

    Returns:
        The current display mode
    """
    if display_buttons[last_display].get_check_state():
        return last_display
    else:
        return impl_get_audience_display(display_buttons, competition)


def impl_get_match_time_by_string(raw: Optional[str]) -> int:
    """Parse a match time string from the UI.

    Args:
        raw: The raw timer string from the UI

    Returns:
        The match time in seconds, or 0 if no valid time is found
    """
    if raw == "" or raw is None:
        return 0
    if ":" in raw:  # Exclude prestart time
        minutes, seconds = raw.split(":")
        return int(minutes) * 60 + int(seconds)
    else:
        return 0


def impl_get_match_time(match_timer_control: HwndWrapper) -> int:
    """Get the current match time.

    Args:
        match_timer_control: The match timer display control

    Returns:
        The current match time in seconds
    """
    raw = impl_get_match_timer_content(match_timer_control)
    return impl_get_match_time_by_string(raw)


def impl_get_prestart_time_by_string(raw: Optional[str]) -> int:
    """Parse a prestart time string from the UI.

    Args:
        raw: The raw timer string from the UI

    Returns:
        The prestart time in seconds, or 0 if no valid time is found
    """
    if raw == "" or raw is None:
        return 0
    if ":" in raw:
        return 0
    return int(raw)


def impl_get_prestart_time(match_timer_control: HwndWrapper) -> int:
    """Get the current prestart time.

    Args:
        match_timer_control: The match timer display control

    Returns:
        The current prestart time in seconds
    """
    raw = impl_get_match_timer_content(match_timer_control)
    return impl_get_prestart_time_by_string(raw)


def impl_get_match_timer_content(match_timer_control: HwndWrapper) -> Optional[str]:
    """Get the raw match timer content from the UI.

    Args:
        match_timer_control: The match timer display control

    Returns:
        The timer content as shown in the UI, or None if not available
    """
    texts = match_timer_control.texts()
    if len(texts) == 0:
        return None
    return texts[0]


def impl_set_current_field_id(field_select: ComboBoxWrapper, field_id: Union[int, str]) -> None:
    """Set the current field ID.

    Args:
        field_select: The field selection combo box control
        field_id: The field ID to select

    Raises:
        ValueError: If the field ID cannot be set in the current state
        IndexError: If the field ID is not valid
    """
    try:
        if field_select.is_enabled():
            field_select.select(field_id)
        else:
            raise ValueError(
                f"Unable to set current field ID. The match might be started already, paused, or ended (need to click Reset Timer)."
            )
    except IndexError:
        raise IndexError(f"Field ID {field_id} is not valid")
    except Exception as e:
        raise ValueError(f"Error setting current field ID: {e}")


def impl_get_match_state(match_state_control: HwndWrapper) -> FieldsetState:
    """Get the current match state.

    Args:
        match_state_control: The match state display control

    Returns:
        The current state of the match
    """
    texts = match_state_control.texts()
    if len(texts) == 0:
        return FieldsetState.Disabled
    return FieldsetState.by_ui_name(texts[0])


def impl_get_current_field_id(field_select: ComboBoxWrapper) -> Optional[int]:
    """Get the current field ID.

    Args:
        field_select: The field selection combo box control

    Returns:
        The current field ID, or None if no field is selected
    """
    index = field_select.selected_index()
    return index if index != 4294967295 else None


def impl_get_match_on_field(match_on_field_control: HwndWrapper) -> Optional[str]:
    """Get the match currently on the field.

    Args:
        match_on_field_control: The match display control

    Returns:
        The match identifier, or None if no match is on the field
    """
    texts = match_on_field_control.texts()
    if len(texts) == 0:
        return None
    return texts[0] or None  # No empty strings


def impl_get_saved_match_results(
    saved_match_results_control: HwndWrapper,
) -> Optional[str]:
    """Get the saved match results.

    Args:
        saved_match_results_control: The match results display control

    Returns:
        The match results, or None if no results are saved
    """
    texts = saved_match_results_control.texts()
    if len(texts) == 0:
        return None
    return texts[0] or None  # No empty strings


def impl_set_autonomous_bonus(
    bonus_button: Dict[FieldsetAutonomousBonus, ButtonWrapper],
    bonus: FieldsetAutonomousBonus,
    competition: Competition,
    active_match_control: HwndWrapper,
) -> None:
    """Set the autonomous bonus.

    Args:
        bonus_button: Dictionary mapping bonus states to their button controls
        bonus: The bonus state to set
        competition: The current competition type
        active_match_control: The active match display control

    Raises:
        ValueError: If autonomous bonus is not available in the current state
    """
    if competition != Competition.V5RC:
        raise ValueError(f"Autonomous bonus is not available for {competition}")
    if impl_get_active_match_type(active_match_control) == FieldsetActiveMatch.Timeout:
        raise ValueError("Autonomous bonus is not available for timeout")
    bonus_button[bonus].click()


def impl_get_autonomous_bonus(
    bonus_buttons: Dict[FieldsetAutonomousBonus, ButtonWrapper],
    competition: Competition,
    active_match_control: HwndWrapper,
) -> FieldsetAutonomousBonus:
    """Get the current autonomous bonus state.

    Args:
        bonus_buttons: Dictionary mapping bonus states to their button controls
        competition: The current competition type
        active_match_control: The active match display control

    Returns:
        The current bonus state

    Raises:
        ValueError: If autonomous bonus is not available in the current state
    """
    if competition != Competition.V5RC:
        raise ValueError(f"Autonomous bonus is not available for {competition}")
    if impl_get_active_match_type(active_match_control) == FieldsetActiveMatch.Timeout:
        raise ValueError("Autonomous bonus is not available for timeout")

    for bonus, button in bonus_buttons.items():
        if button.get_check_state():
            return bonus
    raise ValueError("No bonus found")


def impl_get_autonomous_bonus_lazy(
    bonus_buttons: Dict[FieldsetAutonomousBonus, ButtonWrapper],
    competition: Competition,
    active_match_control: HwndWrapper,
    last_bonus: FieldsetAutonomousBonus,
) -> FieldsetAutonomousBonus:
    """Get the current autonomous bonus state, using a cached value if possible.

    This is an optimization that checks if the last known bonus state is still
    active before doing a full scan of all bonus buttons.

    Args:
        bonus_buttons: Dictionary mapping bonus states to their button controls
        competition: The current competition type
        active_match_control: The active match display control
        last_bonus: The last known bonus state

    Returns:
        The current bonus state
    """
    if bonus_buttons[last_bonus].get_check_state():
        return last_bonus
    else:
        return impl_get_autonomous_bonus(bonus_buttons, competition, active_match_control)


def impl_set_play_sounds(play_sounds_checkbox: ButtonWrapper, play_sounds: bool) -> None:
    """Enable or disable sound effects.

    Args:
        play_sounds_checkbox: The "Play Sounds" checkbox control
        play_sounds: Whether to play sound effects
    """
    current_state = impl_is_play_sounds(play_sounds_checkbox)
    if current_state == play_sounds:
        return
    play_sounds_checkbox.click()


def impl_is_play_sounds(play_sounds_checkbox: ButtonWrapper) -> bool:
    """Check if sound effects are enabled.

    Args:
        play_sounds_checkbox: The "Play Sounds" checkbox control

    Returns:
        True if sound effects are enabled
    """
    return bool(play_sounds_checkbox.get_check_state())


def impl_set_show_results_automatically(
    show_results_automatically_checkbox: ButtonWrapper, show_results_automatically: bool
) -> None:
    """Enable or disable automatic results display.

    Args:
        show_results_automatically_checkbox: The "Show Results Automatically" checkbox control
        show_results_automatically: Whether to show results automatically
    """
    current_state = impl_is_show_results_automatically(show_results_automatically_checkbox)
    if current_state == show_results_automatically:
        return
    show_results_automatically_checkbox.click()


def impl_is_show_results_automatically(
    show_results_automatically_checkbox: ButtonWrapper,
) -> bool:
    """Check if automatic results display is enabled.

    Args:
        show_results_automatically_checkbox: The "Show Results Automatically" checkbox control

    Returns:
        True if results are shown automatically
    """
    return bool(show_results_automatically_checkbox.get_check_state())


def impl_get_active_match_type_by_string(raw: Optional[str]) -> FieldsetActiveMatch:
    """Parse a match type string from the UI.

    Args:
        raw: The raw match type string from the UI

    Returns:
        The type of match currently active
    """
    if raw is None:
        return FieldsetActiveMatch.NoActiveMatch
    elif raw == "TO":
        return FieldsetActiveMatch.Timeout
    else:
        return FieldsetActiveMatch.Match


def impl_get_active_match_type(
    match_on_field_control: HwndWrapper,
) -> FieldsetActiveMatch:
    """Get the type of match currently active.

    Args:
        match_on_field_control: The match display control

    Returns:
        The type of match currently on the field
    """
    match_on_field = impl_get_match_on_field(match_on_field_control)
    return impl_get_active_match_type_by_string(match_on_field)


def impl_get_match_fieldset(title: str) -> WindowSpecification:
    """Get the window for a match fieldset.

    Args:
        title: The window title to find

    Returns:
        The window specification for the fieldset

    Raises:
        WindowNotFoundError: If the window cannot be found
    """
    window_handle = findwindows.find_window(title=title)
    app = Application(backend="win32").connect(handle=window_handle)
    window = app.window(handle=window_handle)
    return window


def impl_get_fieldset_overview(
    audience_display_buttons: Dict[FieldsetAudienceDisplay, ButtonWrapper],
    match_timer_control: HwndWrapper,
    match_state_control: HwndWrapper,
    field_select: ComboBoxWrapper,
    match_on_field_control: HwndWrapper,
    saved_match_results_control: HwndWrapper,
    autonomous_bonus_buttons: Dict[FieldsetAutonomousBonus, ButtonWrapper],
    play_sounds_checkbox: ButtonWrapper,
    show_results_automatically_checkbox: ButtonWrapper,
    competition: Competition,
    last_overview: FieldsetOverview | None,
) -> FieldsetOverview:
    if last_overview is None:
        audience_display = impl_get_audience_display(audience_display_buttons, competition)
        match_timer_content = impl_get_match_timer_content(match_timer_control)
        match_time = impl_get_match_time_by_string(match_timer_content)
        prestart_time = impl_get_prestart_time_by_string(match_timer_content)
        match_state = impl_get_match_state(match_state_control)
        current_field_id = impl_get_current_field_id(field_select)
        match_on_field = impl_get_match_on_field(match_on_field_control)
        saved_match_results = impl_get_saved_match_results(saved_match_results_control)
        autonomous_bonus = impl_get_autonomous_bonus(autonomous_bonus_buttons, competition, match_on_field_control)
        play_sounds = impl_is_play_sounds(play_sounds_checkbox)
        show_results_automatically = impl_is_show_results_automatically(show_results_automatically_checkbox)
        active_match = impl_get_active_match_type_by_string(match_on_field)

        return FieldsetOverview(
            audience_display,
            match_timer_content,
            match_time,
            prestart_time,
            match_state,
            current_field_id,
            match_on_field,
            saved_match_results,
            autonomous_bonus,
            play_sounds,
            show_results_automatically,
            active_match,
        )
    else:
        audience_display = impl_get_audience_display_lazy(
            audience_display_buttons, competition, last_overview.audience_display
        )
        match_timer_content = impl_get_match_timer_content(match_timer_control)
        match_time = impl_get_match_time_by_string(match_timer_content)
        prestart_time = impl_get_prestart_time_by_string(match_timer_content)

        match_state = impl_get_match_state(match_state_control)
        if match_state != FieldsetState.Disabled:
            current_field_id = last_overview.current_field_id
            match_on_field = last_overview.match_on_field
            active_match = last_overview.active_match
        else:
            current_field_id = impl_get_current_field_id(field_select)
            match_on_field = impl_get_match_on_field(match_on_field_control)
            active_match = impl_get_active_match_type_by_string(match_on_field)

        saved_match_results = last_overview.saved_match_results
        autonomous_bonus = last_overview.autonomous_bonus
        play_sounds = last_overview.play_sounds
        show_results_automatically = last_overview.show_results_automatically

        return FieldsetOverview(
            audience_display,
            match_timer_content,
            match_time,
            prestart_time,
            match_state,
            current_field_id,
            match_on_field,
            saved_match_results,
            autonomous_bonus,
            play_sounds,
            show_results_automatically,
            active_match,
        )


def impl_get_team_list(tm_host_ip: str, division_no: int) -> List[Team]:
    """Get the list of teams for a given division.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server
        division_no: The division number

    Returns:
        A list of teams

    Raises:
        Exception: If the teams cannot be fetched
    """

    url = f"http://{tm_host_ip}/division{division_no}/teams"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "html.parser")

        teams = []
        # Find the table containing team data
        table = soup.find("table", {"class": "table"})
        if table and isinstance(table, Tag):
            # Skip header row
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) == 4:  # Ensure we have all columns
                    team = Team(
                        no=cols[0].text.strip(),
                        name=cols[1].text.strip(),
                        location=cols[2].text.strip(),
                        school=cols[3].text.strip(),
                    )
                    teams.append(team)
        return teams
    except Exception as e:
        raise Exception(f"Error fetching teams: {e}")


def impl_get_match_list_V5RC(tm_host_ip: str, division_no: int) -> List[MatchV5RC]:
    """Get the list of matches for a given division.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server
        division_no: The division number
    """

    # TODO

    return []


def impl_get_match_list_VIQRC(tm_host_ip: str, division_no: int) -> List[MatchVIQRC]:
    """Get the list of matches for a given division.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server
        division_no: The division number

    Returns:
        A list of matches

    Raises:
        Exception: If the matches cannot be fetched
    """
    url = f"http://{tm_host_ip}/division{division_no}/matches"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        matches: List[MatchVIQRC] = []
        table = soup.find("table", {"class": "table-centered"})
        if table and isinstance(table, Tag):
            for row in table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 3:  # Ensure we have minimum required columns
                    match_id = cols[0].text.strip()
                    team_1 = cols[1].text.strip()
                    team_2 = cols[2].text.strip()
                    score_text = cols[-1].text.strip()
                    score = float(score_text) if score_text else None
                    match = MatchVIQRC(match_id, team_1, team_2, score)
                    matches.append(match)  # type: ignore
        return matches
    except Exception as e:
        raise Exception(f"Error fetching matches: {e}")


def impl_get_ranking_list_V5RC(tm_host_ip: str, division_no: int) -> List[RankingV5RC]:
    """Get the list of rankings for a given division.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server
        division_no: The division number
    """

    # TODO

    return []


def impl_get_ranking_list_VIQRC(tm_host_ip: str, division_no: int) -> List[RankingVIQRC]:
    """Get the list of rankings for a given division.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server
        division_no: The division number

    Returns:
        A list of rankings

    Raises:
        Exception: If the rankings cannot be fetched
    """

    url = f"http://{tm_host_ip}/division{division_no}/rankings"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rankings: List[RankingVIQRC] = []
        table = soup.find("table", {"class": "table"})
        if table and isinstance(table, Tag):
            for row in table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 3:  # Ensure we have minimum required columns
                    rank = int(cols[0].text.strip())
                    team_no = cols[1].text.strip()
                    matches_played = int(cols[3].text.strip())
                    avg_score = float(cols[4].text.strip())
                    ranking = RankingVIQRC(rank, team_no, matches_played, avg_score)
                    rankings.append(ranking)  # type: ignore
        return rankings
    except Exception as e:
        raise Exception(f"Error fetching rankings: {e}")


def impl_get_skills_ranking_list(tm_host_ip: str) -> List[SkillsRanking]:
    """Get the list of skills rankings.

    Args:
        tm_host_ip: The IP address of the Tournament Manager web server

    Returns:
        A list of skills rankings

    Raises:
        Exception: If the skills rankings cannot be fetched
    """

    url = f"http://{tm_host_ip}/skills/rankings"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rankings = []
        table = soup.find("table", {"class": "table-centered"})
        if table and isinstance(table, Tag):
            for row in table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) == 8:  # Ensure we have all columns
                    ranking = SkillsRanking(
                        rank=int(cols[0].text.strip()),
                        team_no=cols[1].text.strip(),
                        team_name=cols[2].text.strip(),
                        total_score=float(cols[3].text.strip()),
                        prog_high_score=float(cols[4].text.strip()),
                        prog_attempts=int(cols[5].text.strip()),
                        driver_high_score=float(cols[6].text.strip()),
                        driver_attempts=int(cols[7].text.strip()),
                    )
                    rankings.append(ranking)
        return rankings
    except Exception as e:
        raise Exception(f"Error fetching skills rankings: {e}")


class WindowNotFoundError(Exception):
    """Exception raised when a Tournament Manager window cannot be found."""

    def __init__(self, fieldset_title: str) -> None:
        """Initialize the error.

        Args:
            fieldset_title: The title of the window that could not be found
        """
        self.message = f"TM Bridge cannot connect to a Match Field Set dialog titled '{fieldset_title}'. Please ensure that the Match Field Set dialog is open and visible (at least once)."

    def __str__(self) -> str:
        return self.message


def require_window(func):
    """Decorator that ensures a fieldset is connected before calling a method.

    This decorator checks that the fieldset has a valid window connection before
    allowing the method to proceed. If the window is not found, it raises a
    WindowNotFoundError.

    Args:
        func: The method to wrap

    Returns:
        The wrapped method that checks for window connection
    """

    def wrapper(self: Fieldset, *args, **kwargs):
        if not self.is_connected():
            raise WindowNotFoundError(self.get_fieldset_title())
        return func(self, *args, **kwargs)

    return wrapper


class ImplFieldset(Fieldset):
    """Concrete implementation of the Fieldset interface using pywinauto."""

    def __init__(self, competition: Competition, fieldset_title: str) -> None:
        """Initialize a new fieldset implementation.

        Args:
            competition: The type of competition this field is being used for
            fieldset_title: The window title of this fieldset

        Raises:
            WindowNotFoundError: If the window cannot be found
        """
        super().__init__(competition)
        self.fieldset_title = fieldset_title
        try:
            self.set_window(impl_get_match_fieldset(fieldset_title))
        except Exception as e:
            raise WindowNotFoundError(fieldset_title) from e

    def get_window(self) -> Optional[WindowSpecification]:
        """Get the window specification for this fieldset.

        Returns:
            The window specification, or None if not connected
        """
        return self.window

    def reobtain_window(self) -> None:
        """Try to reconnect to the fieldset window."""
        self.set_window(impl_get_match_fieldset(self.fieldset_title))

    def set_window(self, window: Optional[WindowSpecification]) -> None:
        """Set up the window controls for this fieldset.

        This method initializes all the control wrappers needed to interact with
        the fieldset window. If window is None, all controls are cleared.

        Args:
            window: The window specification to use, or None to clear controls
        """
        self.window = window
        if self.window is None:
            return

        self._start_match_button = self.window["Start Match"].wrapper_object()
        self._resume_match_button = self.window["Resume Match"].wrapper_object()
        self._end_early_button = self.window["End Early"].wrapper_object()
        self._abort_match_button = self.window["Abort Match"].wrapper_object()
        self._reset_timer_button = self.window["Reset Timer"].wrapper_object()
        self._audience_display_buttons = {
            display: self.window[display.ui_name].wrapper_object()
            for display in FieldsetAudienceDisplay
            if display.available_for(self.competition)
        }
        self._match_timer_control = self.window["Static3"].wrapper_object()
        self._match_state_control = self.window["Static4"].wrapper_object()
        self._field_select = self.window.ComboBox.wrapper_object()
        self._match_on_field_control = self.window["Static"].wrapper_object()
        self._saved_match_results_control = self.window["Static2"].wrapper_object()
        self._autonomous_bonus_buttons = {
            bonus: self.window[bonus.ui_name].wrapper_object()
            for bonus in FieldsetAutonomousBonus
            if self.competition == Competition.V5RC
        }
        self._play_sounds_checkbox = self.window["Play Sounds"].wrapper_object()
        self._show_results_automatically_checkbox = self.window["Show Results Automatically"].wrapper_object()

        self._last_overview: Optional[FieldsetOverview] = None

    def is_connected(self) -> bool:
        """Check if this fieldset is connected to Tournament Manager.

        Returns:
            True if the fieldset is connected and can be controlled
        """
        return self.window is not None

    def get_fieldset_title(self) -> str:
        """Get the title of this fieldset's window.

        Returns:
            The window title used to identify this fieldset
        """
        return self.fieldset_title

    @require_window
    def get_overview(self, cache: bool = False) -> FieldsetOverview:
        """Get a snapshot of the current field state.

        Args:
            cache: Whether to use cached values for optimization. When True,
                some values that rarely change will be reused from the last
                overview if they haven't changed.
        """
        overview = impl_get_fieldset_overview(
            self._audience_display_buttons,
            self._match_timer_control,
            self._match_state_control,
            self._field_select,
            self._match_on_field_control,
            self._saved_match_results_control,
            self._autonomous_bonus_buttons,
            self._play_sounds_checkbox,
            self._show_results_automatically_checkbox,
            self.competition,
            self._last_overview if cache else None,
        )
        if self._last_overview != overview:  # Only trigger if overview changed
            self.overview_event.trigger(overview)  # Pass overview as argument
        self._last_overview = overview
        return overview

    @require_window
    def start_match(self) -> None:
        impl_start_match(
            self._start_match_button,
            self._resume_match_button,
            self._match_state_control,
        )

    @require_window
    def end_early(self) -> None:
        impl_end_early(self._end_early_button)

    @require_window
    def abort_match(self) -> None:
        impl_abort_match(self._abort_match_button)

    @require_window
    def reset_timer(self) -> None:
        impl_reset_timer(self._reset_timer_button)

    @require_window
    def set_audience_display(self, display: FieldsetAudienceDisplay) -> None:
        impl_set_audience_display(self._audience_display_buttons, display, self.competition)

    @require_window
    def get_audience_display(self) -> FieldsetAudienceDisplay:
        return impl_get_audience_display(self._audience_display_buttons, self.competition)

    @require_window
    def get_match_time(self) -> int:
        return impl_get_match_time(self._match_timer_control)

    @require_window
    def get_prestart_time(self) -> int:
        return impl_get_prestart_time(self._match_timer_control)

    @require_window
    def get_match_timer_content(self) -> Optional[str]:
        return impl_get_match_timer_content(self._match_timer_control)

    @require_window
    def get_match_state(self) -> FieldsetState:
        return impl_get_match_state(self._match_state_control)

    @require_window
    def set_current_field_id(self, field_id: Union[int, str]) -> None:
        impl_set_current_field_id(self._field_select, field_id)

    @require_window
    def get_current_field_id(self) -> Optional[int]:
        return impl_get_current_field_id(self._field_select)

    @require_window
    def get_match_on_field(self) -> Optional[str]:
        return impl_get_match_on_field(self._match_on_field_control)

    @require_window
    def get_saved_match_results(self) -> Optional[str]:
        return impl_get_saved_match_results(self._saved_match_results_control)

    @require_window
    def set_autonomous_bonus(self, bonus: FieldsetAutonomousBonus) -> None:
        impl_set_autonomous_bonus(
            self._autonomous_bonus_buttons,
            bonus,
            self.competition,
            self._match_on_field_control,
        )

    @require_window
    def get_autonomous_bonus(self) -> FieldsetAutonomousBonus:
        return impl_get_autonomous_bonus(
            self._autonomous_bonus_buttons,
            self.competition,
            self._match_on_field_control,
        )

    @require_window
    def set_play_sounds(self, play_sounds: bool) -> None:
        impl_set_play_sounds(self._play_sounds_checkbox, play_sounds)

    @require_window
    def is_play_sounds(self) -> bool:
        return impl_is_play_sounds(self._play_sounds_checkbox)

    @require_window
    def set_show_results_automatically(self, show_results_automatically: bool) -> None:
        impl_set_show_results_automatically(self._show_results_automatically_checkbox, show_results_automatically)

    @require_window
    def is_show_results_automatically(self) -> bool:
        return impl_is_show_results_automatically(self._show_results_automatically_checkbox)

    @require_window
    def get_active_match(self) -> FieldsetActiveMatch:
        return impl_get_active_match_type(self._match_on_field_control)


class ImplTournamentManagerWebServerV5RC(TournamentManagerWebServer[MatchV5RC, RankingV5RC]):
    """Implementation of the Tournament Manager web server interface for V5RC competitions."""

    def __init__(self, tm_host_ip: str) -> None:
        super().__init__(tm_host_ip, Competition.V5RC)

    def get_teams(self, division_no: int) -> List[Team]:
        return impl_get_team_list(self.tm_host_ip, division_no)

    def get_matches(self, division_no: int) -> List[MatchV5RC]:
        return impl_get_match_list_V5RC(self.tm_host_ip, division_no)

    def get_rankings(self, division_no: int) -> List[RankingV5RC]:
        return impl_get_ranking_list_V5RC(self.tm_host_ip, division_no)

    def get_skills_rankings(self) -> List[SkillsRanking]:
        return impl_get_skills_ranking_list(self.tm_host_ip)


class ImplTournamentManagerWebServerVIQRC(TournamentManagerWebServer[MatchVIQRC, RankingVIQRC]):
    """Implementation of the Tournament Manager web server interface for VIQRC competitions."""

    def __init__(self, tm_host_ip: str) -> None:
        super().__init__(tm_host_ip, Competition.VIQRC)

    def get_teams(self, division_no: int) -> List[Team]:
        return impl_get_team_list(self.tm_host_ip, division_no)

    def get_matches(self, division_no: int) -> List[MatchVIQRC]:
        return impl_get_match_list_VIQRC(self.tm_host_ip, division_no)

    def get_rankings(self, division_no: int) -> List[RankingVIQRC]:
        return impl_get_ranking_list_VIQRC(self.tm_host_ip, division_no)

    def get_skills_rankings(self) -> List[SkillsRanking]:
        return impl_get_skills_ranking_list(self.tm_host_ip)


class ImplBridgeEngine(BridgeEngine, ABC):
    """Implementation of the bridge engine using threads for monitoring."""

    def __init__(self, competition: Competition, low_cpu_usage: bool) -> None:
        """Initialize a new bridge engine implementation.

        Args:
            competition: The competition type (V5RC or VIQRC)
            low_cpu_usage: Whether to use low CPU mode. In low CPU mode, the bridge
                engine will use cached values 90% of the time and only do a full
                refresh every 10th iteration (every 100ms).
        """
        super().__init__(competition, low_cpu_usage)
        self._fieldsets: Dict[str, ImplFieldset] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start monitoring all fieldsets.

        This method starts background threads that monitor each fieldset at 100Hz.
        If the engine is already running, this method does nothing.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            # Start monitoring threads for all existing fieldsets
            for title in list(self._fieldsets.keys()):
                self._start_monitoring_thread(title)

    def stop(self) -> None:
        """Stop monitoring all fieldsets.

        This method stops all monitoring threads and waits for them to finish.
        If the engine is not running, this method does nothing.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            # Signal all threads to stop
            for event in self._stop_events.values():
                event.set()
            # Wait for all threads to finish
            for thread in self._threads.values():
                thread.join()
            # Clear thread tracking
            self._threads.clear()
            self._stop_events.clear()

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
        if not self._running:
            raise Exception("Bridge engine is not running")
        with self._lock:
            if title not in self._fieldsets:
                fieldset = ImplFieldset(self.competition, title)
                self._fieldsets[title] = fieldset
                self._start_monitoring_thread(title)
            return self._fieldsets[title]

    def _start_monitoring_thread(self, title: str) -> None:
        """Start a monitoring thread for the given fieldset title.

        Args:
            title: The window title of the fieldset to monitor
        """
        if title in self._threads and self._threads[title].is_alive():
            return

        stop_event = threading.Event()
        self._stop_events[title] = stop_event

        thread = threading.Thread(
            target=self._monitor_fieldset,
            args=(title, stop_event),
            name=f"FieldsetMonitor-{title}",
        )
        thread.daemon = True  # Thread will be killed when main program exits
        self._threads[title] = thread
        thread.start()

    def _monitor_fieldset(self, title: str, stop_event: threading.Event) -> None:
        """Monitor a single fieldset at 100Hz.

        In low CPU mode:
        - Uses cached values 90% of the time
        - Does full refresh every 10th iteration (every 100ms)

        In normal mode:
        - Always does full refresh (no caching)

        Args:
            title: The window title of the fieldset to monitor
            stop_event: Event that signals when monitoring should stop
        """
        fieldset = self._fieldsets[title]
        target_interval = 0.01  # 10ms = 100Hz
        CACHE_CYCLE = 10  # Full refresh every 10th iteration in low CPU mode
        iteration = 0

        while not stop_event.is_set():
            cycle_start = time.time()

            try:
                # Determine if we should use cache based on CPU mode and iteration
                should_use_cache = self.low_cpu_usage and iteration % CACHE_CYCLE != 0
                fieldset.get_overview(cache=should_use_cache)
            except Exception:
                # Window was closed or lost
                fieldset.set_window(None)
                print(f"Fieldset {title} lost connection")
                # Try to recover by reconnecting
                try:
                    fieldset.reobtain_window()
                except Exception:
                    # Still can't find window, wait before retry
                    time.sleep(1.0)
                    continue

            iteration = (iteration + 1) % CACHE_CYCLE

            # Maintain target frequency
            elapsed = time.time() - cycle_start
            sleep_time = max(0.0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)


class ImplBridgeEngineV5RC(ImplBridgeEngine):
    """V5RC-specific bridge engine implementation."""

    def __init__(self, low_cpu_usage: bool) -> None:
        super().__init__(Competition.V5RC, low_cpu_usage)

    def get_web_server(self, tm_host_ip: str) -> "TournamentManagerWebServer[MatchV5RC, RankingV5RC]":
        """Get a V5RC web server instance."""
        return ImplTournamentManagerWebServerV5RC(tm_host_ip)


class ImplBridgeEngineVIQRC(ImplBridgeEngine):
    """VIQRC-specific bridge engine implementation."""

    def __init__(self, low_cpu_usage: bool) -> None:
        super().__init__(Competition.VIQRC, low_cpu_usage)

    def get_web_server(self, tm_host_ip: str) -> "TournamentManagerWebServer[MatchVIQRC, RankingVIQRC]":
        """Get a VIQRC web server instance."""
        return ImplTournamentManagerWebServerVIQRC(tm_host_ip)


@overload
def get_bridge_engine(competition: Literal[Competition.V5RC], low_cpu_usage: bool = True) -> BridgeEngineV5RC: ...


@overload
def get_bridge_engine(competition: Literal[Competition.VIQRC], low_cpu_usage: bool = True) -> BridgeEngineVIQRC: ...


def get_bridge_engine(competition: Competition, low_cpu_usage: bool = True) -> BridgeEngine:
    """Create a new bridge engine instance.

    Args:
        competition: The competition type (V5RC or VIQRC)
        low_cpu_usage: Whether to use low CPU mode (default: True)
            In low CPU mode, the bridge engine will use cached values 90% of the time
            and only do a full refresh every 10th iteration (every 100ms).
            This significantly reduces CPU usage while still maintaining good responsiveness.

    Returns:
        A new bridge engine instance properly typed for the competition
    """
    if competition == Competition.V5RC:
        return ImplBridgeEngineV5RC(low_cpu_usage)
    else:
        return ImplBridgeEngineVIQRC(low_cpu_usage)
