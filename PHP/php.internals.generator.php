<?php

$writeHandle = fopen("php.internals.csv", "w");

foreach(get_defined_functions()["internal"] as $name){
    fputcsv($writeHandle, ['function', $name, null]);
}

foreach(get_declared_classes() as $name){
    fputcsv($writeHandle, ['class', $name, null]);
}

foreach(get_declared_interfaces() as $name){
    fputcsv($writeHandle, ['interface', $name, null]);
}

foreach(get_defined_vars() as $name => $value){
    if(!in_array($name, array('writeHandle', 'name', 'value', 'group', 'groupKey'))){
        fputcsv($writeHandle, ['variable', $name, null]);
    }
}

foreach(get_defined_constants() as $name => $value){

    fputcsv($writeHandle, ['constant', $name, $value]);
}

fclose($writeHandle);
