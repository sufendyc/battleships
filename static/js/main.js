
$(document).ready(function() {

    // If the bot received fragment is present then display the bot received
    // alert and remove the fragment to prevent the alert from displaying if 
    // the user refreshes the page (which they are likely to do in order to get 
    // a progress update)
    if (window.location.hash == "#bot-received") {
        $("#bot-received-alert").show();
        window.location.hash = ""
    }

    // same as above but for the bot missing alert
    if (window.location.hash == "#bot-missing") {
        $("#bot-missing-alert").show();
        window.location.hash = ""
    }

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

    // wire up 'how to' button
    $("#how-to-button").click(function() {
        window.location.href = "/how-to";
    });
});

