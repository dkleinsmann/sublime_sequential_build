import sublime
import sublime_plugin
import functools
import copy
import re
import os

# If we're in Sublime Text 3, we can load the default module quite easily.
if 3000 <= int(sublime.version()):
    exec_mod = getattr( __import__( "Default" ), "exec" )

# In older versions, the loading default module needs some trickery
else:
    import sys

    # Check if the path to Default plugins has been loaded
    seq_bld_default_imported = False
    seq_bld_default_path = os.path.join(sublime.packages_path(), 'Default')
    seq_bld_default_path = os.path.abspath(seq_bld_default_path)
    for path in sys.path:
        if os.path.abspath(path) == seq_bld_default_path:
            seq_bld_default_imported = True

    # If the path is not yet load it, we temporarily load it so we can do import
    #  ExecCommand class from it.
    if not seq_bld_default_imported:
        sys.path.append(os.path.join(sublime.packages_path(), 'Default'))

    # Import the ExecCommand
    exec_mod = __import__( "exec" )

    # Only remove the path if it wasn't there to begin with
    if not seq_bld_default_imported:
        sys.path.remove(os.path.join(sublime.packages_path(), 'Default'))
# Import done

# The ExecCommand class is used for running build commands using Popen
#
# By overloading the on_finished() method, we can trigger a callback when
#  a build completes.
class NotifyingExecCommand(exec_mod.ExecCommand):

    # Store the callback in the class to avoid name clashes.
    callback = None

    # Override the method to issue the callback (if it has been set)
    #  when the build is complete
    def on_finished(self, proc):

        # Retreive the exit code of command. This will decide if the next
        #  command should be run.
        exit_code = proc.exit_code()

        # Do the superclass on_finished() first
        exec_mod.ExecCommand.on_finished( self, proc )

        # Only start the next build step if this one was successful
        if exit_code == 0 or exit_code == None:

            # Issue the callback to the main thread using set_timeout
            if hasattr(self.callback, '__call__'):
                sublime.set_timeout( functools.partial(self.callback), 0 )

# This is the Command class called when a build system sets the
#  target to "sequential_builder".
class SequentialBuilderCommand(sublime_plugin.WindowCommand):

    # This is the regex used to extract build system variables from
    #  arguments passed to this plugin.
    variable_regex = re.compile( r'(\$[{]?)(\w+)([}]?)' )

    # The actual execution method called when the build system begins work
    def run(self, **args):

        # Take the 'build_sequence' argument from the build system
        build_sequence = args.pop("build_sequence", None)

        # Confirm it's a list ([] in the JSON description)
        if isinstance(build_sequence, list):

            # Note down the list of steps, we'll iterate over that list
            #  later.
            self.build_sequence = build_sequence

            # Create all the build system variables so they can be used
            #  in individual build steps
            op = os.path
            var = dict()
            var['packages'] = op.abspath( sublime.packages_path() )

            var['file'] = op.abspath( self.window.active_view().file_name() )
            var['file_path'] = op.dirname( var['file'] )
            var['file_name'] = op.basename( var['file'] )
            base, ext = op.splitext( var['file_name'] )
            var['file_extention'] = ext
            var['file_base_name'] = base

            # <TODO>: Find out how to get current project path.
            #var['project'] = op.abspath(".")
            #var['project_path'] = op.dirname( var['project'] )
            #var['project_name'] = op.basename( var['project'] )
            #base, ext = op.splitext( var['project_name'] )
            #var['project_extention'] = ext
            #var['project_base_name'] = base

            self.variables = var

            # The remaining items in args are the other attributes of the
            #  build system, described in the top level of it's hierarchy.
            # These apply to each step, unless overwridden in the step.
            self.mainArgs = args

            # Set the callback so self.build_step() is run again
            #  when a run_command completes
            NotifyingExecCommand.callback = self.build_step

            # Kick off the first step
            self.step = 0
            self.build_step()

        # Tell the user that they've set up the build system incorrectly.
        else:
            sublime.error_message( "Error: Sequential Builder expects "
                                   "a 'build_sequence' containing a list "
                                   " of 'cmd's. Please check your build "
                                   " system for syntax errors." )

    def _replace_var_str( self, string ):

        # Go through matches in descending order of size. This
        #  stops $file_path being written to as the $file variable
        matches = self.variable_regex.findall( string )
        matches = sorted( matches,
            key=lambda x: len(x[1]),
            reverse=True )

        # <TODO> add default values: (${file_name:default_value})
        # <TODO> file ${file_name/.php/.txt} to replace txt for php
        new_string = string
        for lhs, var, rhs in matches:
            if self.variables.has_key( var ):
                new_string = new_string.replace(
                    "%s%s%s" % (lhs, var, rhs),
                    self.variables[var] )

        return new_string

    def _replace_var_list( self, the_list ):
        new_list = list()
        for item in the_list:
            if type(item) is unicode:
                value = self._replace_var_str( item )
            elif type(item) is list:
                value = self._replace_vars_list( item )
            elif type(item) is dict:
                value = self._replace_vars_dict( item )
            new_list.append( value )
        return new_list

    def _replace_var_dict( self, the_dict ):

        # If the user has tried to use build system variables we try
        #  and populate them.
        for key, value in the_dict.items():

            # Replace user variables in values that are strings
            if type(value) is unicode and "regex" not in key:
                the_dict[key] = self._replace_var_str( value )

            elif type(value) is list:
                the_dict[key] = self._replace_var_list( value )

            elif type(value) is dict:
                the_dict[key] = self._replace_var_dict( value )

        return the_dict

    # Each item in the build sequence corresponds to a call to build_step()
    def build_step( self ):

        # Note which step of the build process is about to be executed
        index = self.step
        self.step += 1

        # Only execute valid build steps
        if ( index < len(self.build_sequence) ):

            # Take a copy of the default attributes for this build step
            args = copy.deepcopy( self.mainArgs )

            # Get the step specific options
            step_args = self.build_sequence[index]

            # And try and populate the build system variables
            step_args = self._replace_var_dict( step_args )

            # Relative paths are relative to the top level working_dir
            #  path.
            if step_args.has_key( 'working_dir' ) and \
               not os.path.isabs( step_args['working_dir'] ):
                step_args['working_dir'] = os.path.join(
                    args['working_dir'],
                    step_args['working_dir'] )

            # Here we update any step specific options
            args.update( step_args )
            args['working_dir'] = os.path.abspath(args['working_dir'])

            # Run the command
            print( "Build Step (%d): %s" % (index+1, args) )
            try:
                self.window.run_command("notifying_exec", args)
            except:
                sublime.error_message( "Error: Sequential Builder triggered an"
                    " unexpected error" )
