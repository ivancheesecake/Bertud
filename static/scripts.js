files = []
queue = []

// Initialize page

$(document).ready(function() {

	// Initialize UI
	$('select').material_select();
	$("#main").height($(window).height()-64);
	$(".collapsible-body").css('max-height',$(window).height()-330);
	$(".collapsible-container").css('height',$(window).height()-200);
	$("#queue").css('height',$(window).height()-120);

	$("#source-folder").val("C:/Data/LAZ_FILES")
	$("#dest-folder").val("E:/FeatureExtractionOutputs")

	// Loop this later
	$("#cpu-pc1").hide();
	$("#ram-pc1").hide();

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
			}
		}
	});
});

function renderFiles(files){
	$(".files-table").html("");

	for(index in files){
		htmlString = "<tr><td>"+files[index]+"</td><td><a href ='#' data-index='"+files[index]+"'class='poplist'><i class='material-icons'>clear</i></a></td></tr>";
		$(".files-table").append(htmlString);
	}

	$(".poplist").click(function(event) {
					
		console.log($(this).data("index"))
		index = files.indexOf($(this).data("index"));
		console.log(index);
		if (index > -1) {
			files.splice(index, 1);
		}	
		console.log(files)
		
		$(this).parent().parent().remove();

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

		success: function(resp){

				directoryExists = resp.exists;
				// console.log(directoryExists)
				if(!directoryExists)
					Materialize.toast('Invalid Output Directory.', 4000,'red lighten-1')

				// Add to Queue
				console.log(emptyList)
				console.log(directoryExists)

				if(!emptyList && directoryExists){

					console.log("Add to queue.");

					path = $('#source-folder').val();

					for(index in files){
						queue.push(path+"/"+files[index]+".laz");
						htmlString = "<li class='collection-item'>"+path+"/"+files[index]+".laz</li>"
						$("#queue-content").append(htmlString);
						
					}

					htmlString = "<span id='queue-badge' class='badge'>+"+files.length+"</span></a>";
					$("#queue-tab").append(htmlString);
					$(".files-table").html('');
					Materialize.toast(files.length+' Files Added to Queue.', 4000,'green lighten-1')
		
				}
			}
	});


});	