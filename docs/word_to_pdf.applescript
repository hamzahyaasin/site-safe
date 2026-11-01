on run argv
	set inPath to item 1 of argv
	set outPath to item 2 of argv
	-- Export the document opened from inPath, found by its name: Word's
	-- active document can be another report left open in Word.
	set docName to do shell script "basename " & quoted form of inPath
	with timeout of 600 seconds
		tell application "Microsoft Word"
			open (POSIX file inPath)
			delay 3
			set theDoc to document docName
			save as theDoc file name outPath file format format PDF
			close theDoc saving no
		end tell
	end timeout
end run
