files = []

// Initialize page

$(document).ready(function() {

	// Initialize UI
	$('select').material_select();
	$("#main").height($(window).height()-64);
	$(".collapsible-body").css('max-height',$(window).height()-300);

	$("#source-folder").val("E:/FeatureExtractionV4/pipelinev6/inputs/raw")

	// Loop this later
	$("#cpu-pc1").hide();
	$("#ram-pc1").hide();

	// Update
	setInterval(function(){

		$.ajax({
			url: 'http://127.0.0.1:5000/listen',
			type: 'GET',
			success: function(resp){
				console.log(resp['1'].cpu,resp['1'].ram);
				update_pcs(resp);

			}
			});
		}, 5000);


});
	
function update_pcs(obj){

	$.each(obj, function(index,o){

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
				console.log(files);
				for(index in files){
					htmlString = "<tr><td>"+files[index]+"</td><td><a href ='#' data-index='"++"'class='poplist'><i class='material-icons'>clear</i></a></td></tr>";
					$(".files-table").append(htmlString);
				}

			}
		}
	});
});

$('#btn-add').click(function(event) {
	alert("HERE");
});	