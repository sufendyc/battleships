$(document).ready(function() {
    // http://bl.ocks.org/tjdecke/5558084

    $('#ship-show').on('click', function(){
    	var $this = $(this);
    	var show = $this.hasClass('show-ships')
    	if(show){
    		$this.text('Hide Ships');
    	} else {
    		$this.text('Show Ships');
    	}
		changeOverlayVisiblily(show);
    	$this.toggleClass('show-ships');
    });

    $('#animation-speed').on('change', function(){
    	animationSpeed = animationSpeeds[$(this).val()];
    });

    // To add -- 
    //		replay current board
    // 		generate new board

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

	for(var a = 0; a < 100; a++){
		var rand = getRandomInt(0, possibleMoves.length - 1);
		var slot = possibleMoves[rand];
		var val = Math.random() <= 0.5 ? -1 : 1;
		randBoard.push([slot, val]);
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
		return "cell bordered " + resultClass[d.result + 1];
	}

	var shipPositions = _.reduce(randBoard, function(acc, val, idx){
		if(val[1] === 1){
			acc.push(val[0]);
		}
		return acc;
	}, []);

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


	var renderOverlay = function(){
		// Draw ship positions
	   	var overlay = svg.selectAll(".ship")
		  .data(shipPositions)
		  .enter()
		  .append("rect")
		  .attr("x", function(d,i) { return emptyBoard[d].xPos + gridSize / 2 / 2 })
		  .attr("y", function(d,i) { return emptyBoard[d].yPos + gridSize / 2 / 2 })
		  .attr("rx", 4)
		  .attr("ry", 4)
		  .attr("class", 'ship')
		  .attr("width", gridSize/2)
		  .attr("height", gridSize/2)
	}
	var changeOverlayVisiblily = function(show){
		var overlay = svg.selectAll(".ship")
		  .classed('hide', function(d) { return !show })
	}

	renderOverlay()

	var res;
	var move;
	var numMovesTotal = randBoard.length;
	var numMovesMade = 0;
	
	// Animation speed vars
	var defaultSpeedIndex = 2; 
	var animationSpeeds = [50, 250, 500, 1000];
	var animationSpeed = animationSpeeds[defaultSpeedIndex];

	// Animate each move in sequence.
	var animate = function(){
		if(numMovesMade < numMovesTotal){
			setTimeout(function(){
				res = randBoard[numMovesMade];
				emptyBoard[res[0]].result = res[1];
				svg.selectAll(".cell")
					.data(emptyBoard)
					.attr('class', function(d, i){
					  	var classStr = genDefaultClases(d);
					  	//  current active move give active class
					  	if(i === numMovesMade){
					  		classStr = classStr + ' active ';
					  	}
					  	return classStr;
					});

				numMovesMade++
				animate();
			}, animationSpeed);
		}
	}

	animate();
});