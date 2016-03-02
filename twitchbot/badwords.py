import logging
import pmxbot

from pmxbot import core, storage
from pmxbot.core import command

LOG = logging.getLogger('pmxbot')


class BadwordsAlreadyBanned(ValueError):
    pass


class BadwordsNotFound(ValueError):
    pass


class Badwords(storage.SelectableStorage):
    def __init__(self):
        self.store = self.from_URI(pmxbot.config.database)

    def initialize(self):
        self._finalizers.append(self.finalize)
        channels = set(pmxbot.config.log_channels).union(set(pmxbot.config.other_channels))
        for channel in channels:
            try:
                badwords = self.store.lookup_channel_bans(channel)
                LOG.info("Setting up contains handlers for %s", channel)
                for badword, punishment in badwords:
                    self._add_handler(badword, channel, punishment)
            except BadwordsNotFound:
                LOG.info("No bad words found for channel %s", channel)

    def finalize(self):
        del self.store

    def add(self, badword, channel, punishment):
        LOG.info("Adding %s to the database for channel %s", badword, channel)
        self._add(badword, channel, punishment)
        LOG.info("Adding contains handler for %s", badword)
        self._add_handler(badword, channel, punishment)
        return True

    def remove(self, badword, channel):
        try:
            targethandler = [handler for handler in pmxbot.core.Handler._registry
                             if isinstance(handler, pmxbot.core.ContainsHandler)
                             and handler.name == badword][0]
        except IndexError:
            raise BadwordsNotFound
        LOG.info("Removing %s from the database for channel %s", badword, channel)
        self._remove(badword, channel)
        LOG.info("Removing contains handler for %s in channel %s", badword, channel)
        pmxbot.core.Handler._registry.remove(targethandler)
        return True

    @classmethod
    def _add_handler(cls, badword, channel, punishment):
        core.contains(
            name=badword,
            channel=channel,
        )(cls.punish)
        LOG.info("Added handler for %s in %s", badword, channel)

    @classmethod
    def punish(cls, client, event, channel, nick, rest): # pylint: disable=too-many-arguments
        if nick == channel.replace('#', ''):
            return
        LOG.info("Someone said something bad")
        for word in rest.split():
            try:
                punishment = cls.store.lookup(word, channel)
                punishment = punishment.format(nick=nick)
                yield punishment
                yield "Hey, %s, enjoy your punishment (%s)"% (nick, punishment)
            except BadwordsNotFound:
                pass


class SQLiteBadwords(Badwords, storage.SQLiteStorage):
    def init_tables(self):
        badwords_db_create = '''
            CREATE TABLE IF NOT EXISTS badwords (
                channel varchar,
                badword varchar,
                punishcmd varchar,
                primary key (channel, badword)
            )
        '''
        self.db.execute(badwords_db_create)
        self.db.commit()

    def lookup(self, word, channel):
        word = word.strip().lower()
        lookup_sql = 'SELECT punishcmd FROM badwords WHERE badword = ? AND channel = ?'
        try:
            punishment = self.db.execute(lookup_sql, [word, channel]).fetchone()[0]
        except:
            raise BadwordsNotFound
        return punishment

    def lookup_channel_bans(self, channel):
        lookup_channel_sql = 'SELECT badword, punishcmd FROM badwords WHERE channel = ?'
        try:
            channelbans = self.db.execute(lookup_channel_sql, (channel,)).fetchall()
        except:
            raise BadwordsNotFound
        return channelbans

    def _add(self, word, channel, punishcmd):
        word = word.strip().lower()
        ban_sql = 'UPDATE badwords SET punishcmd = ? WHERE channel = ? AND badword = ?'
        res = self.db.execute(ban_sql, (punishcmd, word, channel))
        if res.rowcount == 0:
            insert_sql = 'INSERT INTO badwords (badword, channel, punishcmd) VALUES (?, ?, ?)'
            self.db.execute(insert_sql, (word, channel, punishcmd))
        self.db.commit()
        return True

    def _remove(self, word, channel):
        word = word.strip().lower()
        unban_sql = 'DELETE FROM badwords WHERE channel = ? AND badword = ?'
        self.db.execute(unban_sql, (channel, word))
        self.db.commit()
        return True


@command()
def banword(client, event, channel, nick, rest):
    """Add a badword to the database, specify the punishment with the word punish.
    {nick} will be replaced with the offenders nick: '!banword something bad punish /timeout {nick} 60'"""
    # ensure that if quotes are present, they are double quotes
    if nick == channel.replace('#', ''):
        # This command is restricted to the channel owner
        badword, punishment = [part.strip() for part in rest.split('punish')]
        if Badwords.store.add(badword, channel, punishment):
            return "%s, your bad word has been configured" % nick
    else:
        return "I'm sorry %s, that command is restricted to %s" % (nick, channel.replace('#', ''))


@command()
def unbanword(client, event, channel, nick, rest):
    "Remove a banned word from the database"
    try:
        if Badwords.store.remove(rest, channel):
            return "word %s has been unbanned" % (rest)
    except BadwordsNotFound:
        return "%s, %s is not a banned word" % (nick, rest)
