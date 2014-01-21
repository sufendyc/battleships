$( document ).ready(function() {
    // http://bl.ocks.org/tjdecke/5558084


	var table = $('#table');

	var randBoard = [];
	var width = 400;
	var height = 400;
	var rows = 10;
	var gridSize = width/rows;
	var emptyBoard = [];

	for(var a = 0; a < 10; a++){
		for(var b = 0; b < 10; b++){
			emptyBoard.push({
				'xPos': b * gridSize,
				'yPos': a * gridSize,
				'result': 0
			});
		}
	}

	// Generate random board
	var possibleMoves = []
	for(var a = 0; a < 100; a++){
		possibleMoves.push(a);
	}

	function getRandomInt (min, max) {
	    return Math.floor(Math.random() * (max - min + 1)) + min;
	}

	for(var a = 0; a < 30; a++){
		var rand = getRandomInt(0, possibleMoves.length - 1);
		var slot = possibleMoves[rand];
		randBoard.push( {
			'slot': slot,
			'result': Math.random() <= 0.5 ? -1 : 1
		});
		var idx = possibleMoves.indexOf(slot);
		possibleMoves.splice(idx,1);
	}
	// Append initial svg and group
	var svg = d3.select("#board")
			  .append("svg")
	          .attr("width", width)
	          .attr("height", height)
	          .append("g");

	var resultClass = ['miss', 'empty', 'hit'];


	var genDefaultClases = function(d){
		return "cell bordered " + resultClass[d.result + 1]
	}

    // Initialise empty board
   	var board = svg.selectAll(".cell")
	  .data(emptyBoard)
	  .enter()
	  .append("rect")
	  .attr("x", function(d) { return d.xPos })
	  .attr("y", function(d) { return d.yPos })
	  .attr("rx", 4)
	  .attr("ry", 4)
	  .attr("class", function(d){
	  	return genDefaultClases(d);
	  })
	  .attr("width", gridSize)
	  .attr("height", gridSize)

	var res;
	var move;
	var numMovesTotal = randBoard.length;
	var numMovesMade = 0;
	
	// Animate each move in sequence.
	var animate = function(){
		if(numMovesMade < numMovesTotal){
			setTimeout(function(){
				res = randBoard[numMovesMade];
				emptyBoard[res.slot].result = res.result;
				svg.selectAll(".cell")
					.data(emptyBoard)
					.attr('class', function(d, i){
					  	var classStr = genDefaultClases(d);
					  	//  current active board give class
					  	if(i == numMovesMade){
					  		classStr = classStr + ' active ';
					  	}
					  	return classStr;
					});

				numMovesMade++
				animate();
			}, 350);
		}
	}

	animate();
});