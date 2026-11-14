"""Fixed spoken lines, one per event and per failure reason, in both personas (H3).

These are the offline fallback and get cached as audio (`python -m narrator.cache`), so they hold no numbers:
the grounded lines with scores come live from the reasoner. Conversational on purpose: the robot thinks aloud.
Keys: an event name `run.py` says, `help.<Reason value>`, or a persona moment (`obstacle`, `cooldown`, ...).
"""

from common.reasons import Reason

LINES: dict[str, dict[str, str]] = {
    "calm": {
        "perfect": "Okay, that one looks clean. Purple bowl.",
        "defective": "Hmm, there's a mark on this one. Orange bowl.",
        "uncertain": "I'm not sure about this one. Let me take another look.",
        "still_uncertain": "Still can't tell, so I'll play it safe. Orange bowl.",
        "grasp_fail": "Missed it. Let me try that again.",
        "empty": "That's the last one. All done.",
        "quit": "Stopping here and heading home.",
        "dance": "That's the zone empty. Time for a little victory dance.",
        "estop": "Emergency stop. Motors off.",
        "help.grasp_failed": "I can't get a grip on that brick. Could someone give me a hand?",
        "help.brick_lost": "I've lost the brick. I need a hand here.",
        "help.place_failed": "I couldn't get that one into the bowl. Can someone check?",
        "help.timeout": "That move was taking too long, so I stopped. I need a hand.",
        "help.camera": "I can't see through my camera. Could someone check it?",
        "help.inspect_failed": "My inspection just failed. I need someone to take a look.",
        "help.unexpected": "Something unexpected went wrong, so I've gone home. I need a hand.",
        "help.drive_failed": "I couldn't drive all the way to the table. Could someone check my wheels?",
        "drive": "The bricks are out of my reach from here, so I'm driving over to them.",
        "arrived": "I'm in position. Let's start sorting.",
        "drift": "My perfect bricks are scoring closer to the line. The light may have changed, so please rebaseline me.",
        "cooldown": "Ahem. Where was I? Back to work.",
        "halfway": "Right, partner... I mean, right.",  # the cowboy drifting back, so in the calm voice
        "hat_off": "Ohhh, I'm no longer a cowboy... Ahem. Back to business.",
    },
    "cowboy": {
        "perfect": "Clean as a whistle, partner. Purple bowl.",
        "defective": "Well I'll be, there's a mark on this one. Orange bowl it is.",
        "uncertain": "Hold your horses, lemme take another look.",
        "still_uncertain": "Can't rightly tell, so I'm playin' it safe. Orange bowl.",
        "grasp_fail": "Dang, slipped right outta my hand. One more go.",
        "empty": "That's the whole herd. All done.",
        "quit": "Callin' it a day, partner. Headin' home.",
        "dance": "That's the whole herd sorted. Time for a little two-step!",
        "estop": "Whoa there! Motors off.",
        "help.grasp_failed": "Can't get a grip on this little critter. Need a hand, partner.",
        "help.brick_lost": "Lost that brick somewhere on the trail. Need a hand.",
        "help.place_failed": "Couldn't get it in the bowl. Mind checkin', partner?",
        "help.timeout": "That move was draggin' on, so I reined it in. Need a hand.",
        "help.camera": "Can't see a thing out here. Somebody check my camera.",
        "help.inspect_failed": "My lookin' glass just went dark. Need somebody to check it.",
        "help.unexpected": "Somethin' went sideways, so I headed home. Need a hand.",
        "help.drive_failed": "Couldn't ride all the way to the table. Somebody check my wheels.",
        "drive": "Them bricks are out of reach, partner. Movin' the whole outfit over.",
        "arrived": "Whoa there. We're in position. Let's get sortin'.",
        "drift": "Light's shiftin' out here, partner. My scores are driftin', best rebaseline me.",
        "obstacle": "Holy smokes!",
        "hat_on": "Well I'll be, a cowboy hat! Yeehaw, partner. Let's ride.",
        "yeehaw": "Yeehaw!",
        "well_ill_be": "Well I'll be!",
    },
}

# Every event run.py says out loud; tests check each has a line in both personas.
EVENTS = ("perfect", "defective", "uncertain", "still_uncertain", "grasp_fail", "empty", "quit", "estop", "dance", "drift", "drive", "arrived",
          *(f"help.{reason.value}" for reason in Reason))


def key_for(event: str, reason: str | None = None) -> str:
    return f"help.{reason}" if event == "help" and reason else event


def line_for(persona: str, event: str, reason: str | None = None) -> str | None:
    return LINES[persona].get(key_for(event, reason))
