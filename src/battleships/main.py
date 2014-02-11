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
import yaml
from battleships.cache import CacheBotGame
from battleships.conf import Conf
from battleships.data import UsersDataAsync as UsersData
from battleships.queues import QueueBotGame, QueueBotScoring
from bson.objectid import ObjectId


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user_json = self.get_secure_cookie("session")
        if not user_json: 
            return None
        return tornado.escape.json_decode(user_json)


# WWW --------------------------------------------------------------------------

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
    def _on_auth(self, user):

        # set the secure cookie
        if not user:
            raise tornado.web.HTTPError(500, "Facebook auth failed")
        self.set_secure_cookie("session", tornado.escape.json_encode(user))

        # If this is the first time the user has logged in, create a record for
        # them. For simplicity we'll use Facebook's user IDs.
        db = UsersData(self.settings["db"])
        user_doc = yield db.read(user["id"])
        if user_doc is None:
            yield db.create(user)

        self.redirect(self.get_argument("next", "/"))


class MainHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        """Render the homepage, including the leaderboard."""
        ranked_users = yield UsersData(self.settings["db"]).read_ranked_users() 
        self.render("main.html", ranked_users=ranked_users) 

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        """Receive a posted bot file."""

        # check a bot was uploaded
        if "bot_file" not in self.request.files:
            self.redirect("/#bot-missing")

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
        self.redirect("/#bot-received")


class HowToHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        """Render the how to page."""
        self.render("how-to.html")


class PlayHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        """Render the page for showing game visualisations."""

        # get bot data from the database
        user_id = self.get_current_user()["id"]
        user = yield UsersData(self.settings["db"]).read(user_id)

        # convert ObjectIds to strings for JSON serialisation
        bots = user.get("bot_history", [])

        def fmt(bot):
            bot["bot_id"] = str(bot["bot_id"])
            bot["time_human"] = datetime.datetime.fromtimestamp(bot['time']).strftime('%H:%M:%S %Y-%m-%d')
        map(fmt, bots)
        bots = sorted(bots, key=lambda b: -b['time'])
        self.render("play.html", bots=bots, botlen=len(bots))


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


class BotsHandler(APIBaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        """Return details of all the bots submitted by the current user."""

        # get bot data from the database
        user_id = self.get_current_user()["id"]
        user = yield UsersData(self.settings["db"]).read(user_id)

        # convert ObjectIds to strings for JSON serialisation
        bots = user["bots"]
        def fmt(bot):
            bot["bot_id"] = str(bot["bot_id"])
        map(fmt, bots)

        self.complete(data={"bots": bots})
    

class BotGameRequestHandler(APIBaseHandler):

    # TODO enable
    #@tornado.web.authenticated
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

    # TODO enable
    #@tornado.web.authenticated
    def get(self, token):
        """Return the results of a bot game (see BotGameRequestHandler)."""
        result = CacheBotGame.get(token)
        self.complete(data=result)


# Main -------------------------------------------------------------------------

def main():

    # TODO move to logging module
    # init logging
    logging_conf = yaml.load(open("/etc/battleships/logging.yaml"))
    logging.config.dictConfig(logging_conf)

    # load config
    Conf.init()

    # this must happend before we start accepting tornado requests
    db = motor.MotorClient().open_sync().battleships

    # start processing background queues, each in a separate process
    QueueBotGame.start()
    # TODO how does the process access the db? just regular sync mongo!
    QueueBotScoring.start()

    application = tornado.web.Application([

        # WWW
        (r"/",                          MainHandler),               # GET/POST
        (r"/how-to/?",                  HowToHandler),              # GET
        (r"/play/?",                    PlayHandler),               # GET

        # API
        (r"/bots/?",                    BotsHandler),               # GET
        (r"/games/?",                   BotGameRequestHandler),     # POST
        (r"/games/([0-9a-f]{24})/?",    BotGameResultHandler),      # GET
        (r"/auth/login/?",              AuthLoginHandler),          # GET
        ],

        db=             db,
        cookie_secret=  Conf["cookie-secret"],
        fb_app_id=      Conf["fb-app-id"],
        fb_app_secret=  Conf["fb-app-secret"],
        # TODO enable
        #xsrf_cookies=   True,
        login_url=      "/auth/login",
        template_path=  os.path.join(os.path.dirname(__file__), "templates"),
        static_path=    os.path.join(os.path.dirname(__file__), "static"),
        debug=True)
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

