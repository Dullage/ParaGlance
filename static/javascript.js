$(document).ready(function(){
    $("#forecast").load("/get-forecast", function(responseTxt, statusTxt, xhr){
        if(statusTxt == "success")
            $("#loading").hide()
            $("#forecast").show()
        if(statusTxt == "error")
            $("#loading-icon").removeClass("mdi-loading mdi-spin")
            $("#loading-icon").css("color", "#ff7980")
            $("#loading-icon").addClass("mdi-alert")
            $("#loading-text").text("Oops, something is wrong!")
    });
});
