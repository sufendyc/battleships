import datetime
import httplib
import logging.config
import motor
import os.path
import subprocess
import sys
import time
import tornado.auth
import tornado.gen
import tornado.ioloop
import tornado.web
import urlparse
import yaml
from battleships.cache import CacheBotGame
from battleships.conf import Conf
from battleships.data import UsersDataAsync as UsersData
from battleships.queues import QueueBotGame, QueueBotScoring
from bson.objectid import ObjectId
from operator import itemgetter


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user_json = self.get_secure_cookie("session")
        if not user_json: 
            return None
        else:
            user_data = tornado.escape.json_decode(user_json)
            user_data["id"] = ObjectId(user_data["id"])
            return user_data


# WWW --------------------------------------------------------------------------

MSG_NO_BOT = "Oops, looks like you didn't attach the bot file."
MSG_BOT_RECEIVED = \
"""We've received your bot and have queued it for scoring. This process takes \
roughly 20 minutes, so check back then."""

class AuthLoginHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
    # authentication logic based on:
    # https://github.com/facebook/tornado/blob/master/demos/facebook/facebook.py

    @tornado.web.asynchronous
    def get(self):

        redirect_uri = "%s://%s/auth/login?next=%s" % (
            self.request.protocol,
            self.request.host,
            tornado.escape.url_escape(self.get_argument("next", "/")))
        fb_app_id =         self.settings["fb_app_id"]
        fb_app_secret =     self.settings["fb_app_secret"]

        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri=   redirect_uri,
                client_id=      fb_app_id,
                client_secret=  fb_app_secret,
                code=           self.get_argument("code"),
                callback=       self._on_auth)
            return
        self.authorize_redirect(
            redirect_uri=   redirect_uri,
            client_id=      fb_app_id)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def _on_auth(self, facebook_data):

        # set the secure cookie
        if not facebook_data:
            self.settings["log"].warning("Failed Facebook authentication")
            raise tornado.web.HTTPError(httplib.BAD_REQUEST)

        # test whether the Facebook user is recognised
        db = UsersData(self.settings["db"])
        user = yield db.read_by_facebook_id(facebook_data["id"])

        # first login for the user so authenticate them using the verify token
        # then bind the Facebook account to the Experian account
        if user is None:
            verify_token = self._get_verify_token()
            try:
                user_id = yield db.bind(verify_token, facebook_data)
            except Exception as e:
                self.settings["log"].warning("Failed to bind: %s" % e)
                raise tornado.web.HTTPError(httplib.BAD_REQUEST)
        else:
            user_id = user["_id"]

        # write user ID and facebook data to secure session cookie
        session_data = {
            "id":               str(user_id),
            "facebook_data":    facebook_data,
            }
        self.set_secure_cookie(
            "session", tornado.escape.json_encode(session_data))

        self.redirect(self.get_argument("next", "/"))

    def _get_verify_token(self):
        """Attempt to read a verify token from the original query string
        which authenticates a user during their first login.
        """
        arg_next = self.get_argument("next", "/")
        qs = urlparse.parse_qs(urlparse.urlparse(arg_next).query)
        verify_token = qs.get("verify_token")
        if verify_token:
            return verify_token[0]
        else:
            return None


class MainHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        """Render the homepage, including the leaderboard."""
        ranked_users = yield UsersData(self.settings["db"]).read_ranked_users() 
        current_user = self.get_current_user()
        self.render("main.html", 
            ranked_users=ranked_users, 
            current_user=current_user) 

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        """Receive a posted bot file."""

        # check a bot was uploaded
        if "bot_file" not in self.request.files:
            self.render("msg.html", msg=MSG_NO_BOT)

        # save the bot file to disk and make it executable
        bot_id = ObjectId() 
        bot_file_content = self.request.files["bot_file"][0]["body"]
        bot_path = "%s/%s" % (Conf["bot-path"], str(bot_id))
        f = open(bot_path, "w")
        f.write(bot_file_content)
        f.close()
        os.chmod(bot_path, 0744)
        
        # Bot files uploaded from a Windows system cannot natively be executed
        # on a Linux system so run all files through this converter (from
        # the package "tofrodos"). It's harmless running this convert on a 
        # bot uploaded from a Linux system; and easier than detecting the
        # system type.

        # This was causing an error when loading locally
        subprocess.call(["fromdos", bot_path])
    
        # update the user's data with the bot submission
        user_id = self.get_current_user()["id"]
        yield UsersData(self.settings["db"]).\
            update_after_bot_submit(user_id, bot_id)    

        # put the bot in the queue for scoring
        QueueBotScoring.add(user_id, bot_id)

        # display the bot received alert informing the user what happens next
        self.render("msg.html", msg=MSG_BOT_RECEIVED)


class HowToHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        """Render the how to page."""
        self.render("how-to.html")


class GamesHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        """Render the page for showing game visualisations."""

        bot_id = ObjectId(self.get_argument("bot_id"))
        user_id = self.get_current_user()["id"]
        user = yield UsersData(self.settings["db"]).read(user_id)

        # lookup bot number 
        bot_ids = map(itemgetter("bot_id"), user.get("bot_history", []))
        bot_ids.sort(reverse=True)
        bot_num = bot_ids.index(bot_id) + 1

        self.render("games.html", bot_num=bot_num, user=user)


# API --------------------------------------------------------------------------

class APIBaseHandler(BaseHandler):

    def write_error(self, status_code, **kwargs):
        """Overridden to return errors and exceptions in a consistent JSON 
        format.

        Adopted schema used by Instagram:
        http://instagram.com/developer/endpoints/
        """

        exception = kwargs['exc_info'][1]

        # hide details of internal server errors from the client
        if not isinstance(exception, tornado.web.HTTPError):
            exception = tornado.web.HTTPError(httplib.INTERNAL_SERVER_ERROR)
            exception.message = 'Oops, an error occurred.'

        code = getattr(exception, "custom_error_code", status_code)
        self.finish({
            "meta": {
                "error_type":       exception.__class__.__name__,
                "code":             code,
                "error_message":    exception.message,
                }})

    def complete(self, status_code=httplib.OK, data=None):
        """Return data in a consistent JSON format.

        Adopted schema used by Instagram:
        http://instagram.com/developer/endpoints/
        """
        result = {
            "meta": {
                "code": status_code,
                }}
        if data is not None:
            result["data"] = data
        self.set_status(status_code)
        self.write(result)
        self.finish()


class PlayersHandler(APIBaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, user_id):
        user_id = ObjectId(user_id)
        user = yield UsersData(self.settings["db"]).read(user_id)
        self.render("players.html", user=user) 


class BotGameRequestHandler(APIBaseHandler):

    @tornado.web.authenticated
    def post(self):
        """Queue a bot to be played.

        Playing even a single game could take a non-trivial amount of time so
        the bot is added to a queue for processing. A token is returned which
        can be used by the client to check whether the game results are 
        available (see BotGameResultHandler).

        The game results include whether the game was successfully completed
        or whether an error was raised. If successful, then the results
        include information about the ship layout and individual moves made by
        the bot.

        For deterministic games a seed can be provided by the client.

        """
        bot_id = self.get_argument("bot_id")
        seed =   self.get_argument("seed", None)
        token = QueueBotGame.add(bot_id, seed)
        self.complete(data={"token": token})


class BotGameResultHandler(APIBaseHandler):

    @tornado.web.authenticated
    def get(self, token):
        """Return the results of a bot game (see BotGameRequestHandler)."""
        result = CacheBotGame.get(token)
        self.complete(data=result)


# Main -------------------------------------------------------------------------

def main():

    # init logging
    logging_conf = yaml.load(open("/etc/battleships/logging.yaml"))
    logging.config.dictConfig(logging_conf)
    log = logging.getLogger("http")

    # load config
    Conf.init()

    # this must happend before we start accepting tornado requests
    db = motor.MotorClient().open_sync().battleships

    # start processing background queues, each in a separate process
    QueueBotGame.start()
    QueueBotScoring.start()

    application = tornado.web.Application([

        # WWW
        (r"/",                                  MainHandler),
        (r"/how-to/?",                          HowToHandler),
        (r"/games/?",                           GamesHandler),

        # API
        (r"/players/([0-9a-f]{24})/?",          PlayersHandler),
        (r"/games/data?",                       BotGameRequestHandler),
        (r"/games/data/([0-9a-f]{24})/?",       BotGameResultHandler),
        (r"/auth/login/?",                      AuthLoginHandler),
        ],

        log=            log,
        db=             db,
        cookie_secret=  Conf["cookie-secret"],
        fb_app_id=      Conf["fb-app-id"],
        fb_app_secret=  Conf["fb-app-secret"],
        xsrf_cookies=   True,
        login_url=      "/auth/login",
        template_path=  os.path.join(os.path.dirname(__file__), "templates"),
        static_path=    os.path.join(os.path.dirname(__file__), "static"),
        debug=True)
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

