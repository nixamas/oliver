var trellodb = require('../lib/trellodb').connect();
var grocerydb = require('../lib/grocerydb').connect();
var doT = require('express-dot');

exports.show_home = function(req, res){
    console.log("home page requested...");
    res.render('oliver_home', {title: 'Oliver'});
};

exports.see_groceries = function(req, res){
    console.log("showing groceries");
    grocerydb.lookup('Groceries', function(results){
	console.log("Grocery lookup callback function");
	console.log("Found these results " + results);
	res.render('groceries', {title: 'Oliver: Groceries', groceries:results});
    });
};

exports.add_grocery_item = function(req, res){
    console.log("add grocery item");
    var item = {item: req.body['item']};
    grocerydb.insert('Groceries', 
		    item.item,
		    function() {
			    console.log("item added, redirecting to grocery listing");
			    res.redirect('/see-grocery-list');
		    });
		    
};

exports.remove_groceries = function(req, res){
    console.log("removing grocery list");
    grocerydb.archiveitems('Groceries', function(){
	    console.log("items archived");
	    res.render("a_landing_page", {title: 'Oliver'} );
    	});
}

exports.learn_barcode = function(req, res){
//  doT.setGlobals({title: 'Oscar: Learn Barcode'});
  console.log("learning barcode...");
  res.render('learn_barcode', {title: 'Oliver: Learn barcode'});
};

exports.submit_learn_barcode = function(req, res){
  var rule = {barcode: req.body['barcode'], item: req.body['item']};
  trellodb.insert('barcode_rules',
                  rule,
                  function() {
                      res.render('thank_barcode', {title: 'Oscar: Learned barcode',
                                                   rule: rule})
                  });
};
