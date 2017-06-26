<?php
# Copyright (C) 2015 Gerrit Addiks <gerrit@addiks.net>
# https://github.com/addiks/gedit-phpide
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

$definedVars = get_defined_vars();

$writeHandle = fopen("php.internals.csv", "w");

foreach(get_defined_functions()["internal"] as $name){
    fputcsv($writeHandle, ['function', $name]);
}

foreach(get_declared_classes() as $className){
    $reflectionClass = new ReflectionClass($className);

    $classType = "class";

    if ($reflectionClass->isInterface()) {
        $classType = "interface";

    } elseif ($reflectionClass->isTrait()) {
        $classType = "trait";
    }

    /* @var $reflectionParentClass ReflectionClass */
    $reflectionParentClass = $reflectionClass->getParentClass();

    $parentClassName = "";
    if ($reflectionParentClass instanceof ReflectionClass) {
        $parentClassName = $reflectionParentClass->getName();
    }

    $interfaces = implode(",", $reflectionClass->getInterfaceNames());

    $isFinal = $reflectionClass->isFinal();
    $isFinal = ($isFinal ?'true' :'false');

    $isAbstract = $reflectionClass->isAbstract();
    $isAbstract = ($isAbstract ?'true' :'false');

    $docComment = $reflectionClass->getDocComment();

    fputcsv($writeHandle, [
        'class',
        $className,
        $classType,
        $parentClassName,
        $interfaces,
        $isFinal,
        $isAbstract,
        $docComment
    ]);

    foreach ($reflectionClass->getMethods() as $reflectionMethod) {
        /* @var $reflectionMethod ReflectionMethod */

        $methodName = $reflectionMethod->getName();

        $isStatic = $reflectionMethod->isStatic();
        $isStatic = ($isStatic ?'true' :'false');

        $visibility = "public";
        if ($reflectionMethod->isProtected()) {
            $visibility = "protected";

        } elseif ($reflectionMethod->isPrivate()) {
            $visibility = "private";
        }

        $docComment = "";

        $parameters = array();
        foreach ($reflectionMethod->getParameters() as $reflectionParameter) {
            /* @var $reflectionParameter ReflectionParameter */

            $parameterName = $reflectionParameter->getName();

            $parameters[] = $parameterName;
        }
        $parameters = implode(",", $parameters);

        fputcsv($writeHandle, [
            'method',
            $methodName,
            $className,
            $isStatic,
            $visibility,
            $parameters,
            $docComment
        ]);
    }

    foreach ($reflectionClass->getProperties() as $reflectionProperty) {
        /* @var $reflectionProperty ReflectionProperty */

        $memberName = $reflectionProperty->getName();

        $isStatic = $reflectionProperty->isStatic();
        $isStatic = ($isStatic ?'true' :'false');

        $visibility = "public";
        if ($reflectionProperty->isProtected()) {
            $visibility = "protected";

        } elseif ($reflectionProperty->isPrivate()) {
            $visibility = "private";
        }

        $docComment = "";

        fputcsv($writeHandle, [
            'member',
            $memberName,
            $className,
            $isStatic,
            $visibility,
            $docComment
        ]);
    }
}

#foreach(get_declared_interfaces() as $name){
#    fputcsv($writeHandle, ['interface', $name, null]);
#}

foreach($definedVars as $name => $value){
    fputcsv($writeHandle, ['variable', $name, null]);
}

foreach(get_defined_constants() as $name => $value){
    fputcsv($writeHandle, ['constant', $name, $value]);
}

fclose($writeHandle);
