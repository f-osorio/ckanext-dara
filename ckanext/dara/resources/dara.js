/* 
Hendrik Bunke
ZBW - Leibniz Information Centre for Economics

adds some usability to dara metadata forms

*/


$(function metadata_level() {

    $( "#dara_1" ).accordion({
      collapsible: true,
      icons: { "header": "ui-icon-plus", "activeHeader": "ui-icon-minus" },
      active : 0 
    });

    $( "#dara_2" ).accordion({
      collapsible: true,
      icons: { "header": "ui-icon-plus", "activeHeader": "ui-icon-minus" },
      active : 2 // 2 is not a valid option so all levels are inactive
    });

    $( "#dara_3" ).accordion({
      collapsible: true,
      icons: { "header": "ui-icon-plus", "activeHeader": "ui-icon-minus" },
      heightStyle: "content",
      active : 2 // 2 is not a valid option so all levels are inactive
    });

});


$(function add_authors() {
  
  var authorContainer = $('#authors');
   
  $('#add_author').on('click', function() {
    
    $('.hidden_authorfield').clone().prop('class', 'author').appendTo(authorContainer);
    return false;
  });

  //remove author fieldset
  $(authorContainer).on('click', '.remove_author', function() { 
      $(this).parents('fieldset.author').remove();
      return false;
  });
    
});



/* XXX if not using jquery-ui.accordion use this one
$(function publications() {
  
  var publication = $('#dara_Publication');
  var pubs = $('#pubs').text();
  $(publication).hide();
  if( pubs ) {
     $(publication).show();
     $('#add_publication').hide();
  }; 


  $('#add_publication').on('click', function() {
    $(publication).show();
    master_slave_input();
    $('#add_publication').hide();
    return false;
  });

  $('#remove_publication').on('click', function() { 
        $(this).parent().hide();
        $('#add_publication').show();
        return false;
  });
    

});
*/


$(function publication() {
    var publication = $('#dara_Publication');
    var pubs = $('#pubs').text();
    var active = parseInt(pubs);

    $(publication).accordion({
      collapsible: true,
      heightStyle: "content",
      icons: { "header": "ui-icon-plus", "activeHeader": "ui-icon-minus" },
      active : active
    });
});


$(function resource() {
    var resource = $('#dara_Resource');

    $(resource).accordion({
      collapsible: true,
      heightStyle: "content",
      icons: { "header": "ui-icon-plus", "activeHeader": "ui-icon-minus" },
      active : 2
    });

});



//calling master_slave for the first time
$(master_slave_input());

// this is not bind to a jquery document.ready() object since we need to call it
// more than once, for example in add_publication().
function master_slave_input() {

  // conditional field based on input 
    $('.dara_master_slave').each(function () {
      var master = $(this).find('.dara_master').find('input').first();
      var slave = $(this).find('.dara_slave');
      var value = master.prop('value');

      if(value == "") {
        slave.hide();
        }

      master.bind("change keyup paste", function () 
        {
          if(master.prop('value') !="") {
            slave.fadeIn();
          }
          else {
           slave.fadeOut(); 
        }
      });
    });

}

