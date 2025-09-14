//Adds a confirmation popup before submitting the form (or just submit if pmessage == '')
function clickConfirm(pname, pvalue, pmessage="Sure ?") {
    if (pmessage == '' || confirm(pmessage)){
        var f = document.getElementById('theForm');

        var hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = pname;
        hiddenField.value = pvalue;

        f.appendChild(hiddenField);


        //Adds all the range inputs to the form manually
        var ins = document.querySelectorAll('input[type=range]');
        for (var i = 0; i < ins.length; i++) {
            var input = ins[i];

            var hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = input.id;
            hiddenField.value = input.value;
    
            f.appendChild(hiddenField);
        }

        f.submit();
    }
}
