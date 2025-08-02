# MiniTV Video Converter

I have been using a quick and dirty batch file for ages to convert videos to be playable on ESP32 Mini TV's, but recently been enjoying telling AI to do stuff for me. They are especially good at Python in my experience. So I told it what I wanted and it did this. No-one may ever see this so maybe I'll just be uploading it for myself!

Heres a few popular Mini TV projects: 

https://www.instructables.com/Mini-Retro-TV/

https://www.instructables.com/Mini-ESP32-TV-remix/ (my personal favorite) 


Theres an .exe for windows users, so you dont need Python installed, just ensure ffmpeg.exe is in the same directory and open. Select a folder containing your video files, they need to be avi, mkv or mp4. It will process each video and put it into folders (same name as the video file) and rename the outputted video/audio file to match the required names. 

I have tested AVI files and MKV files (upto 1080p) and convert fine but I'd imagine not every format will be perfect, obviously theres the issue of widescreen, most stuff is designed for widescreen, even then some have large borders so its wider again! The encoded videos will have no borders top or bottom but can mean you miss a lot of stuff on the sides. I had tested a lot of different output sizes and felt silly have borders top and bottom on a tiny 1.69" display and made it even harder to see. You can always adjust the settings in the python file if you wish.

Theres also a python version, which *should* work on other operating systems or so AI tells me! 

Theres a few options too, video options depending on the screen you're using and also sound depending on whether your version is setup for AAC or MP3. Theres also a volume adjustment as a lot of these Mini TV's dont have volume adjustment. -5 is louder than -8 so do a few tests as it might depend on your setup/speaker!


<img width="749" height="851" alt="image" src="https://github.com/user-attachments/assets/b03abc25-063b-43af-877b-7dd5781662b2" />



If you do make any adjustments to the python script and want to convert to an exe. Heres the commandline I used: pyinstaller --onefile --windowed --add-data "ffmpeg.exe;." MiniTV-Converter.py (you need Pyinstaller installed via pip install pyinstaller)
