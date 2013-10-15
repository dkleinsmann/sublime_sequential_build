Sublime Sequential Build System
===============================

This plugin serves the purpose of allowing multiple 'cmd' items in a build
system.

To use the plugin set the "target" attribute to "sequential_builder" and
insert a list of build steps.

It is required that the working_dir path be set as an absolute path.
If working_dir is left blank. The directory of the currently open file will be
used.

Warning: If working_dir is specified as a relative path, it is relative to 
the location of the installed plugin.

Warning: The build system variables (ie $project_path) cannot be used in 
individual build steps. The reason for this is that they are resolved outside
of the python plugin framework.

An example build system using multiple build steps:
```JSON
"build_systems":
[
	{
	    "name": "Sequential Build Example (make)",
	    "target": "sequential_builder",
	    "working_dir": "${project_path}/build/",
	    "build_sequence":
	    [
	        {
	            "cmd": ["make", "build"]
	            "file_regex": "^\\s*(.*?)\\((\\d+)\\):\\s+.*$"
	        },
	        {
	            "cmd": ["make", "install"]
	        },
	        {
	            "working_dir": "bin",
	            "cmd": ["./main", "--id", "1"],
	        }
	    ]
	}
]
```
