workers = ["Non-Existent","Cheesecake-PC"]

files = []
queue = []
queueShort = []

// Initialize page

$(document).ready(function() {

	// Initialize UI
	$('select').material_select();
	$("#main").height($(window).height()-64);
	$(".collapsible-body").css('max-height',$(window).height()-330);
	$(".collapsible-container").css('height',$(window).height()-200);
	$("#queue").css('height',$(window).height()-118);
	$("#queue-content").css('height',$(window).height()-192);
	$("#queue-content").parent().css('height',$(window).height()-192);

	//Sakto Lang
	// $("#source-folder").val("E:/FeatureExtractionV4/pipelinev6/inputs/ground")

	//One Lang
	// $("#source-folder").val("E:/testinput")

	// $("#source-folder").val("E:/testinput")

	// $("#dest-folder").val("E:/FeatureExtractionOutputs")

	// Loop this later
	$("#cpu-pc1").hide();
	$("#ram-pc1").hide();

	// Load initial work queue

	$.ajax({
		url: 'http://127.0.0.1:5000/initializeQueue',
		type: 'POST',
		dataType: 'json',
	})
	.success(function(resp) {
		console.log("HERE");
		
		queue = resp.queue;
		console.log(queue)
		for(item in queue){
			tokens = queue[item].path.split("/");
			fname = tokens[tokens.length-1];
			// Currently being processed
			// htmlString = "<li id='"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a class='secondary-content'>Cheesecake-PC</a></div></li>"
			htmlString = "<li id='item"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a href='#' data-id='"+queue[item].itemId+"'class='secondary-content remove-from-queue'><i class='queue-clear material-icons'>clear</i></a></div></li>"
			$("#queue-content").append(htmlString);
			
		}

		$(".remove-from-queue").click(function(event){
			removeFromQueue($(this).data("id"));
		});

	}).error(function() {
		console.log("HERE");
	});
	

	// Update
	setInterval(function(){

		$.ajax({
			url: 'http://127.0.0.1:5000/status',
			type: 'GET',
			success: function(resp){
				update_queue(resp.finished,resp.processing);
				update_pcs(resp.worker_info);
			}
			});
		}
		, 5000);

	
});
	
function update_pcs(obj){

	$.each(obj, function(index,o){
		
		if(o.status==0 || o.cpu==-1){

			$("#status-pc"+index).html("Status: Disconnected");
			$("#panel-pc"+index).addClass('red')
			$("#panel-pc"+index).removeClass('green')
			$("#panel-pc"+index).removeClass('orange')

			$("#cpu-pc"+index).hide();
			$("#ram-pc"+index).hide();
		}

		else{

			console.log(o.status)
			if(o.status==1){
				$("#status-pc"+index).html("Status: Ready");
				$("#panel-pc"+index).addClass('green')
				$("#panel-pc"+index).removeClass('red')
				$("#panel-pc"+index).removeClass('orange')
			}
			else if(o.status==2){
				$("#status-pc"+index).html("Status: Processing");
				$("#panel-pc"+index).addClass('orange')
				$("#panel-pc"+index).removeClass('red')
				$("#panel-pc"+index).removeClass('green')
			}

			$("#cpu-pc"+index).show()
			$("#ram-pc"+index).show()
			$("#cpu-pc"+index).html("CPU: "+o.cpu+"%");
			$("#ram-pc"+index).html("RAM: "+o.ram+"%");
		}	
	});


}

function update_queue(finished,processing){

	console.log("HERE")

	// Update processing

	for(index in processing){
		fname = processing[index].path.split("/").pop();

		// htmlString = "<li id='"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a class='secondary-content'>Cheesecake-PC</a></div></li>"
		htmlString = "<div>"+fname+"<a class='secondary-content'>"+workers[processing[index].worker_id]+"</a></div>"
		$("#item"+processing[index].itemId).html(htmlString)
		
	}


	//$("li[id^='item']")


	// Remove finished elements
	for(index in finished){
		fname = finished[index].path.split("/").pop();
		console.log("#item"+finished[index].itemId);
		$("#item"+finished[index].item_id).remove();

		Materialize.toast(workers[parseInt(finished[index].worker_id)]+' finished processing '+fname+"!", 4000,'green lighten-1')
		
	}


	// for(index in processing){
	// 	fname = finished[index].path.split("/").pop();
	// 	console.log("#item"+finished[index].itemId);
	// 	$("#item"+finished[index].item_id).remove();

	// 	Materialize.toast(workers[parseInt(finished[index].worker_id)]+' finished processing '+fname+"!", 4000,'green lighten-1')
		
	// }

}


$('#btn-source-folder').click(function(event) {

	// alert("HERE");
	data = {"sourcefolder": $("#source-folder").val()}
	console.log(data)
	$.ajax({
		url: 'http://127.0.0.1:5000/inputfolder',
		type: 'POST',
		dataType: 'json',
		data: {"sourcefolder": $("#source-folder").val()},

		success: function(resp){

			
			if(resp.files.length >0){

				files = resp.files;		
				renderFiles(files);

			}

			else{
				$(".files-table").html("");
				Materialize.toast('No LAS/LAZ Files Found in Input Directory Specified.', 4000,'red lighten-1')

			}
		}
	});
});



function renderFiles(files){
	$(".files-table").html("");

	for(index in files){
		// htmlString = "<tr><td>"+files[index]+"</td><td><a href ='#' data-index='"+files[index]+"'class='poplist'><i class='material-icons'>clear</i></a></td></tr>";
		htmlString = "<li class='collection-item'><div>"+files[index]+"<a class='secondary-content poplist' href ='#!' data-index='"+files[index]+"'><i class='material-icons'>clear</i></a></div></li>";
		$(".files-table").append(htmlString);
	}

	$(".poplist").click(function(event) {
					
		console.log($(this).data("index"))
		index = files.indexOf($(this).data("index"));
		console.log(index);

		if (index > -1) {
			files.splice(index, 1);
		}	
		console.log(files);
		
		$(this).parent().parent().fadeOut('fast',function(){$(this).remove();});
		// $(this).parent().parent().remove();

	});
}

$('#queue-tab').click(function(event){
	$('#queue-badge').remove();
});


$('#add-queue').click(function(event) {
	
	// Check list of files
	emptyList = false;
	if(files.length==0){
		emptyList = true;
		Materialize.toast('No files selected.', 4000,'red lighten-1')
	}

	// Check if output directory exists
	directoryExists = false;
	data = {"sourcefolder": $("#source-folder").val()}
	
	$.ajax({
		url: 'http://127.0.0.1:5000/inputfolder',
		type: 'POST',
		dataType: 'json',
		data: {"sourcefolder": $("#dest-folder").val()},
	}).success(function(resp){

		console.log("directoryExists "+resp.exists)
		console.log("emptyList "+emptyList)
		directoryExists = resp.exists;

		inputPath = $('#source-folder').val();
		outputPath = $('#dest-folder').val();

		if(!emptyList && directoryExists)
			addToQueue(files,inputPath,outputPath);

	});


});	

function removeFromQueue(id){

	$.ajax({
		url: 'http://127.0.0.1:5000/removeFromQueue',
		type: 'POST',
		dataType: 'json',
		data: {"removeID": id},
	}).success(function(resp){

		console.log(resp)
		Materialize.toast(resp.path+" has been dequeued.",4000)
		$("#item"+id).remove();


	});

}

function addToQueue(files,inputPath,outputPath){

	queue = []
	queueShort = []
	// console.log(files)

	// No update of UI Yet
	for(index in files){
		// console.log(files[index])
		queue.push(inputPath+"/"+files[index]+".laz");	
		queueShort.push(files[index])	
	}

	// console.log(JSON.stringify(queue))
	// console.log(JSON.stringify(queueShort))

	data = {"files": JSON.stringify(queue), "filesShort":JSON.stringify(queueShort),"outputPath": outputPath};
	// console.log(data)
	$.ajax({
		url: 'http://127.0.0.1:5000/addToQueue',
		type: 'POST',
		dataType: 'json',
		data: data
	}).success(function(resp){
		queue = []
		queueShort = []
		//Update UI
		$("#queue-content").html("")
		queue = resp.queue;
		for(item in queue){
			tokens = queue[item].path.split("/");
			fname = tokens[tokens.length-1];
			// console.log(fname);
			// Currently being processed
			// htmlString = "<li id='"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a class='secondary-content'>Cheesecake-PC</a></div></li>"
			htmlString = "<li id='item"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a href='#' data-id='"+queue[item].itemId+"'class='secondary-content remove-from-queue'><i class='queue-clear material-icons'>clear</i></a></div></li>"
			$("#queue-content").append(htmlString);
			
		}

		$(".remove-from-queue").click(function(event){
			removeFromQueue($(this).data("id"));
		});

		htmlString = "<span id='queue-badge' class='badge'>+"+files.length+"</span></a>";
		$("#queue-tab").append(htmlString);

		Materialize.toast(files.length+' Files Added to Queue.', 4000,'green lighten-1');
		console.log(resp)

		queue = []
		queueShort = []
	});


	// Materialize.toast(files.length+' Files Added to Queue.', 4000,'green lighten-1');
}

$("#view-logs").click(function(event) {
	  
	$.ajax({
		url: 'http://127.0.0.1:5000/getFinished',
		type: 'POST',
		dataType: 'json',
	})
	.success(function(resp) {

		htmlString = "<tr><th>Input File</th><th>Output File</th><th>Start Time</th><th>End Time</th></tr>";

		for(index in resp){

			inputFile = resp[index].path;
			outputFile = resp[index].output_path;
			startTime = resp[index].start_time;
			endTime = resp[index].end_time;

			htmlString+="<tr><td>"+inputFile+"</td>"+"<td>"+outputFile+"</td>"+"<td>"+startTime+"</td>"+"<td>"+endTime+"</td></tr>";
		}


		$("#finished-table").html(htmlString);	
	
	});
	
	$('#logs-modal').openModal();

});