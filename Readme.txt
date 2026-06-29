# What does this toolset do?

	The script attempts to streamline the process of downloading older versions of Riot Games projects
	It utilizes Python, and rman. Check credits for links to codebases.

# Installation

	Once unpacked, place these files and tools into any directory you want, then install the following software

		Required software

			Python 3.10. I am using 3.10.6 personally
			
				Download it from here: 
					https://www.python.org/downloads/release/python-3106/
					
				Install with the following settings
					Install py launcher
					Associate files with Python
					Add Python to environment variables
					(Optional) install for all users
				
			MSVC++ Redistributable packages. These are needed for rman to function correctly
				
				Download the needed versions from here:
					https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170

# Post-Install

	If you have followed the installation instructions, doubleclick download-manager.py and it should open.

	To update the catalog, use the option present in the main menu, or manually overwrite it.

# Archive setup
	
	If you have the archive backups saved, place them in the matching the structure below.
	
		download-manager.py
		Archive\
			<project>\
				bundles\
					<project>.bundle
				releases\
					1234567890ABCDEF.manifest
						
	The archive is effectively a local, read-only cache.