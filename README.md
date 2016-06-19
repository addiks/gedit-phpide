Gedit plugin: PHP IDE functions
===================================

This plugin contains features that are crucial for PHP-development using a project-wide index.

## Features

 * Autocompletion
 * Open declaration
 * Type-View
 * Caller-View (Where is this used?)
 * Automaticly write USE-statements
 * Automaticly add doc-comments to new members
 * Outline (Uses code-folding)
 * Project-wide search
 * Include and Exclude folders from index
 
## Licence

This plugin is licenced under the GNU General Public Licence version 3. 
If you do not know what that means, see the file 'LICENCE'.

## Minimum requirements

 * gedit-3
 * python-3
 
 This plugin is tested under gedit-3.10 under ubuntu 14.04
 
 Currently this plugin will only work on projects using git!
 This limitation will be revoked/fixed in a later version,
 but currently you have to use git.
 
## Download

### Clone the git-repository

Execute the following command:

```
git clone https://github.com/addiks/gedit-phpide.git
```

### Download the zip-archive

https://github.com/addiks/gedit-phpide/archive/master.zip

Extract the zip-archive anywhere you want.

## Installation

1. Move, copy or link the folder you downloaded to ~/.local/share/gedit/plugins/addiks-phpide
2. Restart gedit if it is running.
3. In the menu, go to: Edit > Settings > Plugins
4. Make sure the checkbox next to "Addiks - PHP IDE" is active.

## Set up for project

To be able to use any of the features included in this plugin on your PHP-project, you first have to build the project-index for this projct. This is done by using the Menu 'PHP' > 'Build index'. A new window should pop up showing you the progress of the build. Once the index is built, you are good to go using this plugin.

The PHP-menu will only be visible when having a PHP-file open in gedit. Also make sure that this file is in the project you want to index.

If your project is including external libraries or is generating code which is not part of your codebase or libraries, you probably want to configure the index-includes and excludes before building the index. You can also do this afterwards and update the index, but it is faster to configure the project beforehand.

## Shortcuts

F2: Toggle outline of the current file

F3: Open declaration (of your selection)

F3 + [Alt]: Open type view (of your selection)

F3 + [Ctrl]: Open call view (of your selection)

[Ctrl] + [L]: Open the index-search-window
 