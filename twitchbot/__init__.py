import httplib2
import json
import datetime

import pmxbot

from pmxbot.core import command, on_join, execdelay, contains, regexp
from random import choice

@command(aliases=('ut'))
def uptime(client, event, channel, nick, rest):
    "Show how long the stream has been live for."
    h = httplib2.Http(".cache")
    channelstring = channel.replace('#', '', 1)
    if rest:
        channelstring = rest.split()[0]
    headers, content = h.request("https://api.twitch.tv/kraken/streams/%s" % channelstring)
    if headers['status'] != '200':
        return "Unable to get information for stream %s" % channelstring
    streaminfo = json.loads(content.decode())
    try:
        starttime = streaminfo['stream']['created_at']
    except (KeyError, TypeError):
        return "Unable to get start time for stream %s... is the stream live?" % channelstring
    begin = datetime.datetime.strptime(starttime, '%Y-%m-%dT%H:%M:%SZ')
    end = datetime.datetime.utcnow().replace(microsecond=0)
    return "%s has been broadcasting for %s" % (channelstring, datetime.timedelta(seconds=end.timestamp() - begin.timestamp()))

@command(aliases=('h'))
def help(client, event, channel, nick, rest):
    "Returns help text"
    return "Help command removed"

@execdelay(name="addtwitchcaps", channel='#fakechan', howlong=datetime.timedelta(seconds=2), repeat=False)
def addtwitchcaps(client, event):
    "A testing command"
    client.cap('REQ', ':twitch.tv/membership')
    client.cap('REQ', ':twitch.tv/tags')

@command()
def seppuku(client, event, channel, nick, rest):
    "You have dishonored your family... there is only one option..."
    messages = [
                "{nick} has returned from afar having failed in his mission",
                "After witnessing our disappointment, {nick} knows there is only one option",
                "In accordance with bushido, the ancient honor code of the samurai...",
                "While his family watches, {nick} plunges the knife"
               ]
    yield choice(messages).format(nick=nick)
    yield "/timeout %s 300"
