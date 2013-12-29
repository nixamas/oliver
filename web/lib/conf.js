var yaml = require('js-yaml');
var fs = require('fs');

exports.conf = yaml.load(fs.readFileSync('/etc/oliver.yaml', encoding='utf-8'));
