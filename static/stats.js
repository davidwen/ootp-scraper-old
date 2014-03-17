var Stats = (function() {
  var module = {};

  var getStateObj = function() {
    var start = Number($('.start').text()) - 1;
    var limit = $('.limit').val();
    var sortcol = $('th.sorted').text().trim().toLowerCase();
    var sortdir = $('th.sorted').hasClass('reverse') ? 'asc' : 'desc';
    var min = $('#min').val();
    var showhof = $('input[name=showhof]').is(':checked');
    var showeligible = $('input[name=showeligible]').is(':checked');
    var showactive = $('input[name=showactive]').is(':checked');
    var showretired = $('input[name=showretired]').is(':checked');
    return {
      start: start,
      limit: limit,
      sortcol: sortcol,
      sortdir: sortdir,
      min: min,
      showhof: showhof,
      showeligible: showeligible,
      showactive: showactive,
      showretired: showretired
    };
  };

  var loadState = function() {
    var split = window.location.href.split('#');
    if (split.length < 2) {
      return getStateObj();
    }
    var hash = split[1];
    var params = hash.split('&');
    var state = {};
    for (var ii = 0, len = params.length; ii < len; ii++) {
      var param = params[ii];
      var paramSplit = param.split('=');
      if (paramSplit.length != 2) {
        continue;
      }
      var key = paramSplit[0];
      var val = paramSplit[1];
      if (key.indexOf('show') != -1) {
        $('input[name=' + key + ']').prop('checked', val == 'true');
      }
      state[key] = val;
    }
    return state;
  }

  var saveState = function() {
    var stateObj = getStateObj();
    var state = []
    state.push('start=' + stateObj.start)
    state.push('limit=' + stateObj.limit)
    state.push('sortcol=' + stateObj.sortcol)
    state.push('sortdir=' + stateObj.sortdir)
    state.push('min=' + stateObj.min)
    state.push('showhof=' + stateObj.showhof)
    state.push('showeligible=' + stateObj.showeligible)
    state.push('showactive=' + stateObj.showactive)
    state.push('showretired=' + stateObj.showretired)
    var hash = '#' + state.join('&');
    window.history.replaceState(null, '', window.location.href.split('#')[0] + hash);
    submit(stateObj);
  };

  var submit = function(state) {
    var start = state.start;
    var limit = state.limit;
    var sortcol = state.sortcol;
    var sortdir = state.sortdir;
    var min = state.min;
    var showhof = state.showhof;
    var showeligible = state.showeligible;
    var showactive = state.showactive;
    var showretired = state.showretired;

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
      saveState();
    });

    $('.next-btn').click(function() {
      $('.start').text(Number($('.start').text()) + Number($('.limit').val()));
      saveState();
    });

    $('.prev-btn').click(function() {
      var newStart = Number($('.start').text()) - Number($('.limit').val());
      if (newStart < 1) {
        newStart = 1;
      }
      $('.start').text(newStart);
      saveState();
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
      saveState();
    });

    $('.key-container input').change(function() {
      saveState();
    })

    $('.submit-btn').click(function() {
      saveState();
    });

    var state = loadState();
    submit(state);
  };

  return module;
})();