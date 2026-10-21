on run argv
	set inPath to item 1 of argv
	set outPath to item 2 of argv
	with timeout of 600 seconds
		tell application "Microsoft Word"
			open (POSIX file inPath)
			delay 3
			set theDoc to active document
			save as theDoc file name outPath file format format PDF
			close theDoc saving no
		end tell
	end timeout
end run
