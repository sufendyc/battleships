
$(document).ready(function() {

    // render all timestamps using the 'moments' library
    $("[data-timestamp]").each(function() {
        var ts = $(this).attr("data-timestamp");
        if (ts) {
            var m = moment.unix(ts);
            $(this).
                html(m.fromNow()).
                attr("title", m.format())
        } else {
            $(this).html("-");
        }
    });

    // wire up buttons
    $("#how-to-button").click(function() {
        window.location.href = "/how-to";
    });
    $("#home").click(function() {
        window.location.href = "/";
    });
    $("[data-player-id]").click(function() {
        var playerId = $(this).attr("data-player-id");
        window.location.href = "/players/" + playerId;
    });
    $("[data-bot-id]").click(function() {
        var botId = $(this).attr("data-bot-id");
        window.location.href = "/games?bot_id=" + botId;
    });

});

