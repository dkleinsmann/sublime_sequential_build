import sublime
import sublime_plugin
import functools
import copy

# Import the ExecCommand Class used as a base class for the notifying execution
#  class
import sys, os
sys.path.append(os.path.join(sublime.packages_path(), 'Default'))
ExecCommand = getattr( __import__("exec", fromlist="ExecCommand"),
                       'ExecCommand' )
sys.path.remove(os.path.join(sublime.packages_path(), 'Default'))
# Import done

# The ExecCommand class is used for running build commands using Popen
#
# By overloading the on_finished() method, we can trigger a callback when
#  a build completes.
class NotifyingExecCommand(ExecCommand):

    # Store the callback in the class to avoid name clashes.
    callback = None

    # Override the method to issue the callback (if it has been set)
    #  when the build is complete
    def on_finished(self, proc):

        # Retreive the exit code of command. This will decide if the next
        #  command should be run.
        exit_code = proc.exit_code()

        # Do the superclass on_finished() first
        ExecCommand.on_finished( self, proc )

        # Only start the next build step if this one was successful
        if exit_code == 0 or exit_code == None:

            # Issue the callback to the main thread using set_timeout
            if hasattr(self.callback, '__call__'):
                sublime.set_timeout( functools.partial(self.callback), 0 )

# This is the Command class called when a build system sets the
#  target to "sequential_builder".
class SequentialBuilderCommand(sublime_plugin.WindowCommand):

    # The actual execution method called when the build system begins work
    def run(self, **args):

        # Take the 'build_sequence' argument from the build system
        build_sequence = args.pop("build_sequence")

        # Confirm it's a list ([] in the JSON description)
        if isinstance(build_sequence, list):

            # Note down the list of steps, we'll iterate over that list
            #  later.
            self.build_sequence = build_sequence

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

    # Each item in the build sequence corresponds to a call to build_step()
    def build_step( self ):

        # Note which step of the build process is about to be executed
        index = self.step
        self.step += 1

        # Only execute valid build steps
        if ( index < len(self.build_sequence) ):

            # Take a copy of the default attributes for this build step
            step_args = copy.deepcopy( self.mainArgs )

            # And update them with step specific attributes
            step_args.update( self.build_sequence[index] )

            # Run the command
            print "Build Step (%d): %s" % (index+1, step_args)
            try:
                self.window.run_command("notifying_exec", step_args)
            except:
                sublime.error_message("Error: Sequential Builder triggered an error")
