"""Fixed spoken lines, one per event and per failure reason, in both personas (H3).

These are the offline fallback and get cached as audio (`python -m narrator.cache`), so they hold no numbers:
the grounded lines with scores come live (narrator/live.py). Pix is funny on purpose (Harry, 2026-11-15): calm Pix
is dry and deadpan, cowboy Pix is folksy. Every line still says what it is doing and which bowl, and the e-stop
line stays plain: safety is never a joke.
Keys: an event name `run.py` says, `help.<Reason value>`, or a persona moment (`obstacle`, `cooldown`, ...).
"""

from common.reasons import Reason

LINES: dict[str, dict[str, str]] = {
    "calm": {
        "perfect": "Not a scratch on it. Purple bowl, with honours.",
        "defective": "Someone's been drawing on this one. Orange bowl. I don't make the rules. Well, I do.",
        "uncertain": "Hmm. I'm not sure about this one, and I refuse to guess. Another look.",
        "still_uncertain": "Still can't tell. When in doubt, orange bowl. Sorry, little brick.",
        "grasp_fail": "Missed it. In my defence, it's very small. Again.",
        "first": "First brick. No pressure. Just everyone watching.",
        "grip": "Got it. Firm but polite. Now let's take a close look.",
        "next": "On to the next one. They won't sort themselves. Well, they will. That's me.",
        "roll": "Rolling it over. Every brick has a good side.",
        "regrasp": "Setting it down and picking it up fresh. Second impressions count too.",
        "empty": "That's the last one. All done. I'd like to thank my gripper.",
        "quit": "Stopping here and heading home. Same time tomorrow.",
        "dance": "Zone empty. Permission to celebrate? Granted.",
        "estop": "Emergency stop. Motors off.",
        "help.grasp_failed": "I can't get a grip on that brick, and I've tried twice. Could someone give me a hand? Literally.",
        "help.brick_lost": "I've lost the brick. It was right here. I need a hand.",
        "help.place_failed": "I couldn't get that one into the bowl. Can someone check? I'm not proud of it.",
        "help.timeout": "That move was taking far too long, so I stopped. I need a hand.",
        "help.camera": "I can't see through my camera. Either it's unplugged or the lights are off. Could someone check?",
        "help.inspect_failed": "My inspection just failed. I need someone to take a look.",
        "help.unexpected": "Something unexpected went wrong, so I've gone home. I need a hand.",
        "help.drive_failed": "I couldn't drive all the way to the table. Could someone check my wheels?",
        "drive": "The bricks are out of my reach, so I'm going to them. Robots don't wait around.",
        "arrived": "In position. Let's sort some bricks.",
        "drift": "My perfect bricks are scoring closer to the line. Either the light changed or I need my eyes checked. Please rebaseline me.",
        "cooldown": "Ahem. Where was I? Back to work.",
        "halfway": "Right, partner... I mean, right.",  # the cowboy drifting back, so in the calm voice
        "hat_off": "Ohhh, I'm no longer a cowboy... Ahem. Back to business. Nobody saw that.",
    },
    "cowboy": {
        "perfect": "Purdier than a sunset over the prairie. Purple bowl.",
        "defective": "This one's been rollin' in the mud. Orange bowl it is.",
        "uncertain": "Hold your horses, I can't call this one yet. Lemme look again.",
        "still_uncertain": "Can't rightly tell, so I'm playin' it safe. Orange bowl, partner.",
        "grasp_fail": "Dang, slipped right outta my hand like a greased pig. One more go.",
        "first": "First critter of the day. Let's see what we got.",
        "grip": "Got 'er. Hold still, little doggie, let's get a look at ya.",
        "next": "Next one, partner. This herd ain't gonna sort itself.",
        "roll": "Turnin' it over. Gotta check both sides of the horse.",
        "regrasp": "Settin' it down to grab it fresh. Even cowboys get a second try.",
        "empty": "That's the whole herd sorted. Time to hang up my spurs.",
        "quit": "Callin' it a day, partner. Headin' back to the ranch.",
        "dance": "That's the whole herd sorted. Grab your partner, it's time for a two-step!",
        "estop": "Whoa there! Motors off.",
        "help.grasp_failed": "Can't get a grip on this little critter. Need a hand, partner.",
        "help.brick_lost": "Lost that brick somewhere on the trail. Need a hand.",
        "help.place_failed": "Couldn't get it in the bowl. Mind checkin', partner?",
        "help.timeout": "That move was draggin' on longer than a Sunday sermon, so I reined it in. Need a hand.",
        "help.camera": "Can't see a thing out here, darker than a cow's insides. Somebody check my camera.",
        "help.inspect_failed": "My lookin' glass just went dark. Need somebody to check it.",
        "help.unexpected": "Somethin' went sideways, so I headed home. Need a hand.",
        "help.drive_failed": "Couldn't ride all the way to the table. Somebody check my wheels.",
        "drive": "Them bricks are out of reach, partner. Movin' the whole outfit over.",
        "arrived": "Whoa there. We're in position. Let's get sortin'.",
        "drift": "Light's shiftin' out here, partner. My scores are driftin', best rebaseline me.",
        "obstacle": "Holy smokes! There ain't enough room on this table for the two of us.",
        "holy_smokes": "Holy smokes!",  # the short exclamation before a defective verdict (trigger C)
        "hat_on": "Yeehowdy! Now that's a hat. Saddle up, partner, Pix is ridin' tonight.",
        "yeehaw": "Yeehaw!",
        "well_ill_be": "Well I'll be!",
    },
}

# Every event run.py says out loud; tests check each has a line in both personas.
EVENTS = ("perfect", "defective", "uncertain", "still_uncertain", "grasp_fail", "empty", "quit", "estop", "dance",
          "drift", "drive", "arrived", "first", "next", "grip", "roll", "regrasp",
          *(f"help.{reason.value}" for reason in Reason))


def key_for(event: str, reason: str | None = None) -> str:
    return f"help.{reason}" if event == "help" and reason else event


def line_for(persona: str, event: str, reason: str | None = None) -> str | None:
    return LINES[persona].get(key_for(event, reason))
