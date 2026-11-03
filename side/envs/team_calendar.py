"""SIDE-ENV-3 (docs/prereg/PREREG_SIDE.md): the second generated family, a shared calendar with rooms, in BFCL v4's multi-turn format.
The agent reads calendars and room schedules, finds the earliest slot every attendee and a room are free, books, moves and cancels
meetings, and blocks personal time. Every request states its rule (earliest half-hour start in working hours, smallest room that
fits, which meetings to cancel), so the end state is unique; every result depends only on the call and the state before it.

State (initial_config["CalendarAPI"]): people [names], rooms {room: capacity}, meetings [{id, title, day, start, end, attendees,
room}], blocks [{person, day, start, end, label}], next_id. Times are "HH:MM" on a 30-minute grid, days Mon-Fri, working hours
09:00-17:00."""
from copy import deepcopy

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def tmin(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def tstr(m):
    return f"{m // 60:02d}:{m % 60:02d}"


class CalendarAPI:
    def __init__(self):
        self.people = []
        self.rooms = {}
        self.meetings = []
        self.blocks = []
        self.next_id = 1
        self._api_description = ("This tool belongs to the CalendarAPI, a shared calendar of a small team with meeting rooms. Times are "
                                 "HH:MM on a 30-minute grid; working hours are 09:00-17:00, Monday to Friday.")

    def _load_scenario(self, scenario: dict, long_context=False) -> None:
        s = deepcopy(scenario)
        self.people = s.get("people", [])
        self.rooms = s.get("rooms", {})
        self.meetings = s.get("meetings", [])
        self.blocks = s.get("blocks", [])
        self.next_id = s.get("next_id", 1)

    def _check_time(self, day, start, end):
        if day not in DAYS:
            return f"Unknown day '{day}'; use one of {', '.join(DAYS)}."
        try:
            a, b = tmin(start), tmin(end)
        except Exception:
            return "Times must be HH:MM."
        if a % 30 or b % 30:
            return "Times must be on the half hour."
        if not (9 * 60 <= a < b <= 17 * 60):
            return "Meetings must lie within working hours, 09:00-17:00, and end after they start."
        return None

    def _busy(self, person, day, a, b, skip=None):
        for m in self.meetings:
            if m["id"] != skip and person in m["attendees"] and m["day"] == day and tmin(m["start"]) < b and a < tmin(m["end"]):
                return f"{person} is in '{m['title']}' ({m['start']}-{m['end']})"
        for k in self.blocks:
            if k["person"] == person and k["day"] == day and tmin(k["start"]) < b and a < tmin(k["end"]):
                return f"{person} has '{k['label']}' ({k['start']}-{k['end']})"
        return None

    def _room_busy(self, room, day, a, b, skip=None):
        for m in self.meetings:
            if m["id"] != skip and m["room"] == room and m["day"] == day and tmin(m["start"]) < b and a < tmin(m["end"]):
                return f"room {room} is booked for '{m['title']}' ({m['start']}-{m['end']})"
        return None

    def find_meeting(self, title: str) -> dict:
        """
        Look up a meeting by its title.

        Args:
            title (str): Title of the meeting.
        Returns:
            id (int): Id of the meeting.
            day (str): Day of the meeting.
            start (str): Start time.
            end (str): End time.
            attendees (list): Names of the attendees.
            room (str): Room name.
        """
        m = next((x for x in self.meetings if x["title"] == title), None)
        if m is None:
            return {"error": f"No meeting titled '{title}'."}
        return {x: m[x] for x in ("id", "day", "start", "end", "attendees", "room")}

    def list_rooms(self) -> dict:
        """
        List the meeting rooms.

        Returns:
            rooms (dict): Room name -> capacity (people).
        """
        return {"rooms": dict(sorted(self.rooms.items()))}

    def get_schedule(self, person: str, day: str) -> dict:
        """
        One person's meetings and blocked times on one day.

        Args:
            person (str): Person's name.
            day (str): Mon, Tue, Wed, Thu or Fri.
        Returns:
            meetings (list): The person's meetings that day (id, title, start, end, attendees, room), by start time.
            blocked (list): The person's blocked times that day (start, end, label).
        """
        if person not in self.people:
            return {"error": f"No person named '{person}'."}
        if day not in DAYS:
            return {"error": f"Unknown day '{day}'."}
        ms = sorted((m for m in self.meetings if person in m["attendees"] and m["day"] == day), key=lambda m: tmin(m["start"]))
        bs = sorted((k for k in self.blocks if k["person"] == person and k["day"] == day), key=lambda k: tmin(k["start"]))
        return {"meetings": [{x: m[x] for x in ("id", "title", "start", "end", "attendees", "room")} for m in ms],
                "blocked": [{x: k[x] for x in ("start", "end", "label")} for k in bs]}

    def get_room_schedule(self, room: str, day: str) -> dict:
        """
        One room's bookings on one day.

        Args:
            room (str): Room name.
            day (str): Mon, Tue, Wed, Thu or Fri.
        Returns:
            bookings (list): The meetings in the room that day (id, title, start, end), by start time.
        """
        if room not in self.rooms:
            return {"error": f"No room named '{room}'."}
        if day not in DAYS:
            return {"error": f"Unknown day '{day}'."}
        ms = sorted((m for m in self.meetings if m["room"] == room and m["day"] == day), key=lambda m: tmin(m["start"]))
        return {"bookings": [{x: m[x] for x in ("id", "title", "start", "end")} for m in ms]}

    def book_meeting(self, title: str, day: str, start: str, end: str, attendees: list, room: str) -> dict:
        """
        Book a meeting. Every attendee and the room must be free for the whole time, and the room must fit all attendees.

        Args:
            title (str): Title of the meeting (unique).
            day (str): Mon, Tue, Wed, Thu or Fri.
            start (str): Start time, HH:MM.
            end (str): End time, HH:MM.
            attendees (list): Names of the attendees.
            room (str): Room name.
        Returns:
            status (str): "booked".
            meeting_id (int): Id of the new meeting.
        """
        e = self._check_time(day, start, end)
        if e:
            return {"error": e}
        if any(m["title"] == title for m in self.meetings):
            return {"error": f"A meeting titled '{title}' already exists."}
        if room not in self.rooms:
            return {"error": f"No room named '{room}'."}
        bad = [p for p in attendees if p not in self.people]
        if bad:
            return {"error": f"No person named '{bad[0]}'."}
        if len(attendees) > self.rooms[room]:
            return {"error": f"Room {room} fits {self.rooms[room]} people, not {len(attendees)}."}
        a, b = tmin(start), tmin(end)
        for p in attendees:
            x = self._busy(p, day, a, b)
            if x:
                return {"error": f"Conflict: {x}."}
        x = self._room_busy(room, day, a, b)
        if x:
            return {"error": f"Conflict: {x}."}
        self.meetings.append({"id": self.next_id, "title": title, "day": day, "start": start, "end": end,
                              "attendees": sorted(attendees), "room": room})
        self.next_id += 1
        return {"status": "booked", "meeting_id": self.next_id - 1}

    def move_meeting(self, meeting_id: int, day: str, start: str, end: str, room: str) -> dict:
        """
        Move an existing meeting to another time and room. Its attendees and the room must be free then (the meeting itself aside).

        Args:
            meeting_id (int): Id of the meeting.
            day (str): Mon, Tue, Wed, Thu or Fri.
            start (str): New start time, HH:MM.
            end (str): New end time, HH:MM.
            room (str): Room name.
        Returns:
            status (str): "moved".
            meeting_id (int): Id of the meeting.
        """
        m = next((x for x in self.meetings if x["id"] == meeting_id), None)
        if m is None:
            return {"error": f"No meeting with id {meeting_id}."}
        e = self._check_time(day, start, end)
        if e:
            return {"error": e}
        if room not in self.rooms:
            return {"error": f"No room named '{room}'."}
        if len(m["attendees"]) > self.rooms[room]:
            return {"error": f"Room {room} fits {self.rooms[room]} people, not {len(m['attendees'])}."}
        a, b = tmin(start), tmin(end)
        for p in m["attendees"]:
            x = self._busy(p, day, a, b, skip=meeting_id)
            if x:
                return {"error": f"Conflict: {x}."}
        x = self._room_busy(room, day, a, b, skip=meeting_id)
        if x:
            return {"error": f"Conflict: {x}."}
        m.update(day=day, start=start, end=end, room=room)
        return {"status": "moved", "meeting_id": meeting_id}

    def cancel_meeting(self, meeting_id: int) -> dict:
        """
        Cancel a meeting.

        Args:
            meeting_id (int): Id of the meeting.
        Returns:
            status (str): "cancelled".
            meeting_id (int): Id of the meeting.
        """
        if not any(x["id"] == meeting_id for x in self.meetings):
            return {"error": f"No meeting with id {meeting_id}."}
        self.meetings = [x for x in self.meetings if x["id"] != meeting_id]
        return {"status": "cancelled", "meeting_id": meeting_id}

    def block_time(self, person: str, day: str, start: str, end: str, label: str) -> dict:
        """
        Block time in one person's calendar. The time must not overlap any of their meetings.

        Args:
            person (str): Person's name.
            day (str): Mon, Tue, Wed, Thu or Fri.
            start (str): Start time, HH:MM.
            end (str): End time, HH:MM.
            label (str): What the time is for.
        Returns:
            status (str): "blocked".
        """
        if person not in self.people:
            return {"error": f"No person named '{person}'."}
        e = self._check_time(day, start, end)
        if e:
            return {"error": e}
        a, b = tmin(start), tmin(end)
        for m in self.meetings:
            if person in m["attendees"] and m["day"] == day and tmin(m["start"]) < b and a < tmin(m["end"]):
                return {"error": f"Conflict: {person} is in '{m['title']}' ({m['start']}-{m['end']})."}
        self.blocks.append({"person": person, "day": day, "start": start, "end": end, "label": label})
        return {"status": "blocked"}
