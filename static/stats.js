var Stats = (function() {
  var module = {};

  var submit = function() {
    var start = Number($('.start').text()) - 1;
    var limit = $('.limit').val();
    var sortcol = $('th.sorted').text().trim().toLowerCase();
    var sortdir = $('th.sorted').hasClass('reverse') ? 'asc' : 'desc';
    var min = $('#min').val();
    var showhof = $('input[name=showhof]').is(':checked');
    var showeligible = $('input[name=showeligible]').is(':checked');
    var showactive = $('input[name=showactive]').is(':checked');
    var showretired = $('input[name=showretired]').is(':checked');

    $.ajax({
      type: 'GET',
      url: window.location.pathname + '/table',
      data: {
        start: start,
        limit: limit,
        sortcol: sortcol ? sortcol : 'war',
        sortdir: sortdir,
        min: min,
        showhof: showhof,
        showeligible: showeligible,
        showactive: showactive,
        showretired: showretired
      },
      success: function(html) {
        $('#stats-table').html(html);
        var total = Number($('input[name=total]').val());
        var start = Number($('input[name=start]').val());
        var end = Number($('input[name=end]').val());
        var min = Number($('input[name=min]').val());
        $('.total').text(total);
        $('.start').text(start);
        $('.end').text(end);
        $('#min').val(min);
        if (start == 1) {
          $('.prev-btn').attr('disabled', true);  
        } else {
          $('.prev-btn').removeAttr('disabled');
        }
        if (end >= total) {
          $('.next-btn').attr('disabled', true);  
        } else {
          $('.next-btn').removeAttr('disabled');
        }
      }
    });
  };

  module.bind = function() {
    $('.multiselect').multiselect({});

    $('.limit').change(function() {
      submit();
    });

    $('.next-btn').click(function() {
      $('.start').text(Number($('.start').text()) + Number($('.limit').val()));
      submit();
    });

    $('.prev-btn').click(function() {
      var newStart = Number($('.start').text()) - Number($('.limit').val());
      if (newStart < 1) {
        newStart = 1;
      }
      $('.start').text(newStart);
      submit();
    });

    $('#stats-table').on('click', '.subheader th', function() {
      if ($(this).hasClass('sorted')) {
        if ($(this).hasClass('reverse')) {
          $(this).removeClass('reverse');
        } else {
          $(this).addClass('reverse');
        }
      } else {
        $('.sorted').removeClass('sorted');
        $(this).addClass('sorted');
      }
      submit();
    });

    $('.key-container input').change(function() {
      submit();
    })

    $('.submit-btn').click(function() {
      submit();
    }).click();
  };

  return module;
})();