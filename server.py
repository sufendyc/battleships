import motor
import os.path
import sys
import tornado.auth
import tornado.gen
import tornado.ioloop
import tornado.web
import yaml
from bson.objectid import ObjectId
from data import UsersDataAsync as UsersData
from queue import BotQueue


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user_json = self.get_secure_cookie("session")
        if not user_json: 
            return None
        return tornado.escape.json_decode(user_json)


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
        bot_path = "%s/%s" % (self.settings["bot_path"], bot_id)
        f = open(bot_path, "w")
        f.write(bot_file_content)
        os.chmod(bot_path, 0744)

        # update the user's data with the bot submission
        user_id = self.get_current_user()["id"]
        yield UsersData(self.settings["db"]).\
            update_bot_pending(user_id, bot_id)    

        # put the bot in the queue for processing
        BotQueue.add(user_id, bot_id)

        # display the bot recevied alert informing the user what happens next
        self.redirect("/#bot-received")


class HowToHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        """Render the how to page."""
        self.render("how-to.html") 


def main():

    # load config
    with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
        conf = yaml.load(f)

    # this must happend before we start accepting tornado requests
    db = motor.MotorClient().open_sync().battleships

    application = tornado.web.Application([
        (r"/",              MainHandler),
        (r"/how-to",        HowToHandler),
        (r"/auth/login",    AuthLoginHandler),
        ],
        db=             db,
        cookie_secret=  conf["cookie-secret"],
        fb_app_id=      conf["fb-app-id"],
        fb_app_secret=  conf["fb-app-secret"],
        bot_path=       conf["bot-path"],
        xsrf_cookies=   True,
        login_url=      "/auth/login",
        template_path=  os.path.join(os.path.dirname(__file__), "templates"),
        static_path=    os.path.join(os.path.dirname(__file__), "static"),
        debug=True)
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

