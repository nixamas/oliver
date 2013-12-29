var Trello = require('node-trello');
var oliver_conf = require('./conf').conf;

var trello_api = new Trello(oliver_conf['trello_app_key'], oliver_conf['trello_token']);

// Turns Trello into a DB.
function GroceryDB() {
  var _table_name_cache = {};

  // Returns a Trello list ID for the given table
  //
  // Passes the ID to the given callback.
  this._with_list_id = function(table_name, cb) {
    if (_table_name_cache[table_name] !== undefined) {
      cb(_table_name_cache[table_name]);
      return;
    }

    trello_api.get('1/board/' + oliver_conf['trello_grocery_board'] + '/lists', function(err, data) {
        var db_lists = data.filter(function(db_list) {return (db_list['name'] == table_name)});

        if (db_lists.length == 0) {
          console.log('No list named "' + table_name + '"');
          res.send(500, 'No list named "' + table_name + '"');
          return;
        }
        _table_name_cache[table_name] = db_lists[0]['id'];
        cb(_table_name_cache[table_name]);
    });
  }
}


// Returns all items in the given table for which the given callback returns true.
//
// If provided, `filter_callback` will be used to filter the result set.
// `result_callback(result_rows)` will be called when the lookup is complete.
GroceryDB.prototype.lookup = function(table, filter_callback, result_callback) {
  // Allow filter_callback to be omitted.
  if (result_callback === undefined) {
    result_callback = filter_callback;
    filter_callback = undefined;
  }

  this._with_list_id(table, function(list_id) {
    trello_api.get('1/list/' + list_id + '/cards/open', function(err, data) {
      var cards = data;
      var rows = cards.map(function(card) { return card['name'] });

      if (filter_callback === undefined) { filter_callback = function(x) { return true } }
      result_callback(rows.filter(filter_callback));
    });
  });
}

// Adds the given item to the given table.
//
// callback() will be called when the insert is complete.
GroceryDB.prototype.insert = function(table, item, callback) {
  this._with_list_id(table, function(list_id) {
    trello_api.post('1/list/' + list_id + '/cards', {name: item}, function(err) {
      if (err) { console.log(err); }
      callback();
    });
  });
}

GroceryDB.prototype.archiveitems = function(table, callback) {
  this._with_list_id(table, function(list_id) {
    trello_api.post('1/lists/' + list_id + '/archiveAllCards', function(err){
      if (err) {console.log(err);}
      callback();
    });	    
  });
}

exports.connect = function() { return new GroceryDB() };
