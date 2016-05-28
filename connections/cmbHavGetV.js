var fs = require('fs');

global.load = function (file) {
    var body = fs.readFileSync(file, {encoding:'utf8'});
    eval.call(global, body);
};

load(process.argv[2])
console.log(getV(process.argv[3]));
