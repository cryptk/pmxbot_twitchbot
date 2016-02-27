import logging
import pmxbot

from pmxbot import core, storage
from pmxbot.core import command

log = logging.getLogger('pmxbot')

class BadwordsAlreadyBanned(ValueError):
    pass


class BadwordsNotFound(ValueError):
    pass


class Badwords(storage.SelectableStorage):
    @classmethod
    def initialize(self):
        self.store = self.from_URI(pmxbot.config.database)
        self._finalizers.append(self.finalize)
        channels = set(pmxbot.config.log_channels).union(set(pmxbot.config.other_channels))
        for channel in channels:
            try:
                badwords = self.store.lookupChannelBans(channel)
                log.info("Setting up contains handlers for %s" % channel)
                for badword, punishment in badwords:
                    self._add_handler(badword, channel, punishment)
            except BadwordsNotFound:
                log.info("No bad words found for channel %s" % channel)

    @classmethod
    def finalize(cls):
        del cls.store

    def add(self, badword, channel, punishment):
        log.info("Adding %s to the database for channel %s" % (badword, channel))
        self._add(badword, channel, punishment)
        log.info("Adding contains handler for %s" % badword)
        self._add_handler(badword, channel, punishment)
        return True

    def remove(self, badword, channel):
        try:
            targethandler = [handler for handler in pmxbot.core.Handler._registry if type(handler) == pmxbot.core.ContainsHandler and handler.name == badword][0]
        except IndexError:
            raise BadwordsNotFound
        log.info("Removing %s from the database for channel %s" % (badword, channel))
        self._remove(badword, channel)
        log.info("Removing contains handler for %s in channel %s" % (badword, channel))
        pmxbot.core.Handler._registry.remove(targethandler)
        return True

    @classmethod
    def _add_handler(cls, badword, channel, punishment):
        core.contains(
            name=badword,
            channel=channel,
        )(cls.punish)
        log.info("Added handler for %s in %s" % (badword, channel))

    @classmethod
    def punish(cls, client, event, channel, nick, rest):
        if nick == channel.replace('#',''):
            return
        log.info("Someone said something bad")
        for word in rest.split():
            try:
                punishment = cls.store.lookup(word, channel)
                punishment = punishment.format(nick=nick)
                yield(punishment)
                yield("Hey, %s, enjoy your punishment (%s)" % (nick, punishment))
            except BadwordsNotFound:
                pass


class SQLiteBadwords(Badwords, storage.SQLiteStorage):
    def init_tables(self):
        BADWORDS_DB_CREATE = '''
            CREATE TABLE IF NOT EXISTS badwords (
                channel varchar,
                badword varchar,
                punishcmd varchar,
                primary key (channel, badword)
            )
        '''
        self.db.execute(BADWORDS_DB_CREATE)
        self.db.commit()

    def lookup(self, word, channel):
        word = word.strip().lower()
        LOOKUP_SQL = 'SELECT punishcmd FROM badwords WHERE badword = ? AND channel = ?'
        try:
            punishment = self.db.execute(LOOKUP_SQL, [word, channel]).fetchone()[0]
        except:
            raise BadwordsNotFound
        return punishment

    def lookupChannelBans(self, channel):
        LOOKUP_CHANNEL_SQL = 'SELECT badword, punishcmd FROM badwords WHERE channel = ?'
        #try:
        channelbans = self.db.execute(LOOKUP_CHANNEL_SQL, (channel,)).fetchall()
        #except:
        #    raise BadwordsNotFound
        return channelbans

    def _add(self, word, channel, punishcmd):
        word = word.strip().lower()
        BAN_SQL = 'UPDATE badwords SET punishcmd = ? WHERE channel = ? AND badword = ?'
        res = self.db.execute(BAN_SQL, (punishcmd, word, channel))
        if res.rowcount == 0:
            INSERT_SQL = 'INSERT INTO badwords (badword, channel, punishcmd) VALUES (?, ?, ?)'
            ins = self.db.execute(INSERT_SQL, (word, channel, punishcmd))
        self.db.commit()
        return True

    def _remove(self, word, channel):
        word = word.strip().lower()
        UNBAN_SQL = 'DELETE FROM badwords WHERE channel = ? AND badword = ?'
        res = self.db.execute(UNBAN_SQL, (channel, word))
        self.db.commit()
        return True


@command()
def banword(client, event, channel, nick, rest):
    "Add a badword to the database, specify the punishment with the word punish, {nick} will be replaced with the offenders nick: '!banword something bad punish /timeout {nick} 60'"
    # ensure that if quotes are present, they are double quotes
    if nick == channel.replace('#', ''):
        #This command is restricted to the channel owner
        badword, punishment = [part.strip() for part in rest.split('punish')]
        if Badwords.store.add(badword, channel, punishment):
            return("%s, your bad word has been configured" % nick)
    else:
        return("I'm sorry %s, that command is restricted to %s" % (nick, channel.replace('#','')))

@command()
def unbanword(client, event, channel, nick, rest):
    "Remove a banned word from the database"
    try:
        if Badwords.store.remove(rest, channel):
            return("word %s has been unbanned" % (rest))
    except BadwordsNotFound:
        return("%s, %s is not a banned word" % (nick, rest))
