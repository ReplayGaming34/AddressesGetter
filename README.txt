Hello to whoever is unlucky enough to read this!



This is a really niche software I wrote for my friend, he needed something that will take images and change their location.


PRIOR TO RUNNING THE PROGRAM:
	In the program files you cloned there's a folder marked Images, copy the images you'd like to alter into that folder, I've included 5 sample images

	
	to run as an .exe make sure you have pyinstaller installed, if not run pip install pyinstaller on cmd
	
	then to make it an executable run pyinstaller --onefile -w "PATH TO FILE"

after turning it into an executable follow the instructions

INSTRUCTION OF USE:

1: Locate the folder marked Important then --> dist --> then click on the application file

2: Hit the first Browse button under the ExifTool Path entry field, then navigate to the program files --> exiftool-13.34_64 --> exiftool.exe --> open

3: Hit the second Browse button under the Merged CSV File entry field, navigate back to the program files then click pa_addresses_merged

4: Hit the final Browse button under the Select Folder of Images entry field, navigate to the program files and select the folder marked Images

5: In the final entry field type in the street names you'd like the program to pull addresses from. Separate by a comma if you have multiple(ex: Hearthstone Road, Wertzville Road)

6: Hit apply, it takes a minute to run. After it's finished a window should come up saying "Should have worked maybe"(Just a joke, if this comes up it definitely worked)

7: Congratulations! The images in the Images folder are now altered and can be downloaded with a different location assigned to them