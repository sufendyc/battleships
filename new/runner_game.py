
class GameRunner(object):

    def run(bot_path, game_class, game_seed=None):

        # all games have a seed so they can be replayed
        game_seed = game_seed or random.random()

        try:
            game = game_class(game_seed)
            history = [(None, None, game.get_state)]
            while not game.is_complete():
                bot_request = game.get_bot_request()
                bot_response = self._call_bot(bot_path, bot_request)
                accepted = game.update_with_bot_response(bot_response):
                if not accepted:
                    raise BotIllegalMoveException(bot_response)
                game_state = game.get_state()
                history.append((bot_request, bot_response, game_state))

            score = game.get_score
            result = {
                "success":          True,
                "score":            score,
                "history":          history,
                "game_seed":        game_seed,
                }

        except BotException as e:
            # handle all bot errors here
            result = {
                "success":          False,
                "history":          history,
                "game_seed":        game_seed,
                "bot_request":      bot_request,
                "error_type":       e.error_type,
                "error_message":    e.error_message,
                }
            result.update(e.extra)

        return result

    def _invoke_bot(self, bot_path, bot_move_request_string):
        # may raise error
        pass

