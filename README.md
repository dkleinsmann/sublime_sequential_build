Sublime Sequential Build System
===============================

This plugin allows build system with multiple 'cmd' steps that will get
executed sequentially.

To use the plugin set the "target" attribute to "sequential_builder" and
insert a list of build steps.

Note: It is required that the working_dir path be set as an absolute path.
For this reason it is recommended that one of the following variables are used.
```
$file_path
$project_path
```

Note: Some build system variables cannot be used in the individual build steps.
The allowed variables are listed below.
```
$file_path
$file
$file_name
$file_extension
$file_base_name
$packages
```

Warning: Snippets and default values for variables are not yet supported.

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
                "cmd": ["make", "${file}"]
                "file_regex": "^\\s*(.*?)\\((\\d+)\\):\\s+.*$"
            },
            {
                "cmd": ["make", "install"]
            },
            {
                "working_dir": "../bin",
                "cmd": ["$file_base_name", "--id", "1"],
            }
        ]
    }
]
```
