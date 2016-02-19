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

	//Madami
	//$("#source-folder").val("E:/FeatureExtractionV4/pipelinev6/inputs/raw")

	$("#source-folder").val("E:/testinput")
	$("#dest-folder").val("E:/FeatureExtractionOutputs")

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
			alert($(this).data("id"));
		});

	}).error(function() {
		console.log("HERE");
	});
	

	// Update
	// setInterval(function(){

		// $.ajax({
		// 	url: 'http://127.0.0.1:5000/status',
		// 	type: 'GET',
		// 	success: function(resp){
		// 		console.log(resp['1'].cpu,resp['1'].ram);
		// 		update_pcs(resp);

		// 	}
		// 	});
		// }, 5000);

	
});
	
function update_pcs(obj){

	$.each(obj, function(index,o){
		console.log(index);
		console.log(o.status);
		if(o.status==0 || o.cpu==-1){

			$("#status-pc"+index).html("Status: Disconnected");
			$("#panel-pc"+index).addClass('red')
			$("#panel-pc"+index).removeClass('green')

			$("#cpu-pc"+index).hide();
			$("#ram-pc"+index).hide();
		}

		else{

			if(o.status==1){
				$("#status-pc"+index).html("Status: Ready");
				$("#panel-pc"+index).addClass('green')
				$("#panel-pc"+index).removeClass('red')
			}
			else if(o.status==2){
				$("#status-pc"+index).html("Status: Processing");

			}

			$("#cpu-pc"+index).show()
			$("#ram-pc"+index).show()
			$("#cpu-pc"+index).html("CPU: "+o.cpu+"%");
			$("#ram-pc"+index).html("RAM: "+o.ram+"%");
		}	
	});


}



//E:\FeatureExtractionV4\pipelinev6\inputs\raw

// $('#btn-source-folder').click(function(event) {

// 	// alert("HERE");
// 	data = {"sourcefolder": $("#source-folder").val()}
// 	console.log(data)
// 	$.ajax({
// 		url: 'http://127.0.0.1:5000/inputfolder',
// 		type: 'POST',
// 		dataType: 'json',
// 		data: {"sourcefolder": $("#source-folder").val()},

// 		success: function(resp){

			
// 			if(resp.files.length >0){

// 				files = resp.files;		
// 				renderFiles(files);

// 			}

// 			else{
// 				$(".files-table").html("");
// 				Materialize.toast('No LAS/LAZ Files Found in Input Directory Specified.', 4000,'red lighten-1')

// 			}
// 		}
// 	});
// });

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

// $('#add-queue').click(function(event) {
	
// 	// Check list of files
// 	emptyList = false;
// 	if(files.length==0){
// 		emptyList = true;
// 		Materialize.toast('No files selected.', 4000,'red lighten-1')
// 	}

// 	// Check if output directory exists
// 	directoryExists = false;
// 	data = {"sourcefolder": $("#source-folder").val()}
	
// 	$.ajax({
// 		url: 'http://127.0.0.1:5000/inputfolder',
// 		type: 'POST',
// 		dataType: 'json',
// 		data: {"sourcefolder": $("#dest-folder").val()},

// 		success: function(resp){

// 				directoryExists = resp.exists;
// 				// console.log(directoryExists)
// 				if(!directoryExists)
// 					Materialize.toast('Invalid Output Directory.', 4000,'red lighten-1')

// 				// Add to Queue
// 				console.log(emptyList)
// 				console.log(directoryExists)

// 				if(!emptyList && directoryExists){

// 					console.log("Add to queue.");

// 					path = $('#source-folder').val();

// 					for(index in files){
// 						queue.push(path+"/"+files[index]+".laz");
// 						htmlString = "<li class='collection-item'>"+path+"/"+files[index]+".laz</li>"
// 						$("#queue-content").append(htmlString);
						
// 					}

// 					htmlString = "<span id='queue-badge' class='badge'>+"+files.length+"</span></a>";
// 					$("#queue-tab").append(htmlString);
// 					$(".files-table").html('');
// 					Materialize.toast(files.length+' Files Added to Queue.', 4000,'green lighten-1')
		
// 				}
// 			}
// 	});


// });	


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

function addToQueue(files,inputPath,outputPath){

	// No update of UI Yet
	for(index in files){
		queue.push(inputPath+"/"+files[index]+".laz");	
		queueShort.push(files[index])	
	}

	data = {"files": JSON.stringify(queue), "filesShort":JSON.stringify(queueShort),"outputPath": outputPath};
	console.log(data)
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
			// Currently being processed
			// htmlString = "<li id='"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a class='secondary-content'>Cheesecake-PC</a></div></li>"
			htmlString = "<li id='item"+queue[item].itemId+"'class='collection-item'><div>"+fname+"<a href='#' data-id='"+queue[item].itemId+"'class='secondary-content remove-from-queue'><i class='queue-clear material-icons'>clear</i></a></div></li>"
			$("#queue-content").append(htmlString);
			
		}

		$(".remove-from-queue").click(function(event){
			alert($(this).data("id"));
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
	  $('#logs-modal').openModal();
});