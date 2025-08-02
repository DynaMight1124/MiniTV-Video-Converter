import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import subprocess
import threading
import sys
import time
import shutil
import platform

# --- Configuration ---
# You can easily change the accepted file formats here.
ACCEPTED_FORMATS = ('.avi', '.mp4', '.mkv')

# --- End of Configuration ---

def get_ffmpeg_path():
    """
    Determines the path to the ffmpeg executable, accommodating PyInstaller and different OS.
    """
    executable_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (e.g., by PyInstaller)
        return os.path.join(sys._MEIPASS, executable_name)
    else:
        # If run as a normal Python script
        return executable_name

FFMPEG_EXE = get_ffmpeg_path()


class ConverterApp:
    """
    A GUI application for converting video files using FFmpeg.
    """
    def __init__(self, root):
        """
        Initializes the main application window.
        """
        self.root = root
        self.root.title("MiniTV Video Converter")
        self.root.geometry("600x650")
        self.root.resizable(False, False)
        self.input_directory = ""
        self.is_converting = False
        self.stop_requested = False
        self.current_process = None # To hold the running FFmpeg process

        # --- UI Elements ---
        # Frame for directory selection
        self.dir_frame = tk.Frame(root, padx=10, pady=10)
        self.dir_frame.pack(fill=tk.X)

        self.dir_label = tk.Label(self.dir_frame, text="Video Directory:")
        self.dir_label.pack(side=tk.LEFT, padx=(0, 5))

        self.dir_entry = tk.Entry(self.dir_frame, state='readonly', width=60)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.browse_button = tk.Button(self.dir_frame, text="Browse...", command=self.browse_directory)
        self.browse_button.pack(side=tk.LEFT, padx=(5, 0))

        # --- Conversion Options ---
        self.options_frame = tk.Frame(root, padx=10, pady=5)
        self.options_frame.pack(fill=tk.X)

        # Video Options
        video_options_frame = ttk.LabelFrame(self.options_frame, text="Video Output Options", padding=(10, 5))
        video_options_frame.pack(fill=tk.X, pady=5)
        
        self.video_option = tk.StringVar(value="288x240")
        tk.Radiobutton(video_options_frame, text="288x240 Display", variable=self.video_option, value="288x240").pack(anchor='w')
        tk.Radiobutton(video_options_frame, text="320x240 Display", variable=self.video_option, value="320x240").pack(anchor='w')

        # Audio Options
        audio_options_frame = ttk.LabelFrame(self.options_frame, text="Audio Output Options", padding=(10, 5))
        audio_options_frame.pack(fill=tk.X, pady=5)

        self.audio_format = tk.StringVar(value="aac")
        tk.Radiobutton(audio_options_frame, text="AAC Audio", variable=self.audio_format, value="aac").pack(anchor='w')
        tk.Radiobutton(audio_options_frame, text="MP3 Audio", variable=self.audio_format, value="mp3").pack(anchor='w')
        
        volume_frame = tk.Frame(audio_options_frame)
        volume_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(volume_frame, text="Volume Adjustment:").pack(side=tk.LEFT, padx=(18, 5))
        self.audio_volume = tk.StringVar(value="-8dB")
        tk.Entry(volume_frame, textvariable=self.audio_volume, width=10).pack(side=tk.LEFT)
        tk.Label(volume_frame, text="(e.g., -8dB is quieter than -5dB)").pack(side=tk.LEFT, padx=(5, 0))


        # --- Controls and Status ---
        self.control_frame = tk.Frame(root, padx=10, pady=5)
        self.control_frame.pack(fill=tk.X)
        
        button_container = tk.Frame(self.control_frame)
        button_container.pack()

        self.start_button = tk.Button(button_container, text="Start Conversion", command=self.start_conversion_thread, state=tk.DISABLED, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_container, text="Stop Conversion", command=self.request_stop, state=tk.DISABLED, width=15)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(self.control_frame, text="")
        self.status_label.pack(pady=(5,0))


        # --- Progress Log ---
        self.log_frame = tk.Frame(root, padx=10, pady=10)
        self.log_frame.pack(expand=True, fill=tk.BOTH)
        
        self.log_label = tk.Label(self.log_frame, text="Progress Log:")
        self.log_label.pack(anchor='w')

        self.log_text = scrolledtext.ScrolledText(self.log_frame, state='disabled', wrap=tk.WORD, height=15)
        self.log_text.pack(expand=True, fill=tk.BOTH)

    def log_message(self, message):
        """Logs a message to the text area in a thread-safe way."""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def browse_directory(self):
        """Opens a dialog to select the input directory."""
        directory = filedialog.askdirectory(title="Select Folder with Videos")
        if directory:
            self.input_directory = directory
            self.dir_entry.config(state='normal')
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, self.input_directory)
            self.dir_entry.config(state='readonly')
            self.start_button.config(state=tk.NORMAL)
            self.log_message(f"Selected directory: {self.input_directory}")

    def start_conversion_thread(self):
        """Disables the start button and starts the conversion and timer threads."""
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.browse_button.config(state=tk.DISABLED)
        
        self.is_converting = True
        self.stop_requested = False
        
        conversion_thread = threading.Thread(target=self.run_conversion)
        conversion_thread.daemon = True
        conversion_thread.start()
        
        timer_thread = threading.Thread(target=self.update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        
    def request_stop(self):
        """Requests to stop the conversion process after confirmation, using OS-specific commands."""
        if messagebox.askyesno("Confirm Stop", "Are you sure you want to stop the conversion?\nThe current file will be cancelled immediately."):
            self.stop_requested = True
            self.log_message("\n--- STOP REQUESTED BY USER ---")
            if self.current_process:
                self.log_message(f"Forcefully terminating FFmpeg process (PID: {self.current_process.pid})...")
                try:
                    if platform.system() == "Windows":
                        # Use taskkill on Windows to terminate the process and its children (/T) forcefully (/F).
                        subprocess.run(
                            f"taskkill /PID {self.current_process.pid} /F /T",
                            check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        # Use kill on Unix-like systems (macOS, Linux)
                        os.kill(self.current_process.pid, 9) # 9 is SIGKILL for forceful termination
                    self.log_message("Process terminated.")
                except (subprocess.CalledProcessError, OSError) as e:
                    self.log_message(f"Could not terminate process (it may have already finished): {e}")
                except Exception as e:
                    self.log_message(f"An error occurred while trying to terminate the process: {e}")
            self.stop_button.config(state=tk.DISABLED)

    def update_timer(self):
        """Updates an elapsed time label every second while conversion is active."""
        start_time = time.time()
        while self.is_converting:
            elapsed_seconds = int(time.time() - start_time)
            self.status_label.config(text=f"Converting... Time Elapsed: {elapsed_seconds}s")
            time.sleep(1)
        self.status_label.config(text="")

    def run_conversion(self):
        """The main conversion logic that finds files and runs FFmpeg."""
        start_time = time.time()
        self.log_message("--- Starting Conversion Process ---")
        
        try:
            video_files = [f for f in os.listdir(self.input_directory) if f.lower().endswith(ACCEPTED_FORMATS)]
            
            if not video_files:
                self.log_message("No video files found in the selected directory.")
                messagebox.showinfo("Information", "No video files with the specified formats were found.")
                return

            self.log_message(f"Found {len(video_files)} video file(s) to convert.")

            for filename in video_files:
                if self.stop_requested:
                    self.log_message("\nConversion process stopped by user.")
                    break
                
                self.process_file(filename)
            
            if not self.stop_requested:
                end_time = time.time()
                total_duration = end_time - start_time
                duration_str = time.strftime("%M minutes and %S seconds", time.gmtime(total_duration))
                
                self.log_message(f"\n--- Conversion Process Finished in {duration_str} ---")
                messagebox.showinfo("Success", f"All video conversions are complete!\nTotal time taken: {duration_str}")

        except Exception as e:
            self.log_message(f"An error occurred: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        finally:
            self.is_converting = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.browse_button.config(state=tk.NORMAL)

    def run_ffmpeg_command(self, command, filename):
        """Runs an FFmpeg command and allows it to be terminated."""
        popen_kwargs = {
            'shell': True,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True
        }
        if platform.system() == "Windows":
            popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
        try:
            self.current_process = subprocess.Popen(command, **popen_kwargs)
            stdout, stderr = self.current_process.communicate()
            
            if self.stop_requested:
                return 'stopped'

            if self.current_process.returncode != 0:
                self.log_message(f"ERROR processing {filename}.")
                self.log_message(f"FFmpeg stderr: {stderr}")
                return 'error'
            else:
                return 'success'

        except Exception as e:
            self.log_message(f"An exception occurred while running FFmpeg: {e}")
            return 'error'
        finally:
            self.current_process = None

    def process_file(self, filename):
        """Processes a single video file based on the selected GUI options."""
        input_filepath = os.path.join(self.input_directory, filename)
        file_basename = os.path.splitext(filename)[0]
        output_dir = os.path.join(self.input_directory, file_basename)
        
        video_choice = self.video_option.get()
        audio_format_choice = self.audio_format.get()
        audio_volume_choice = self.audio_volume.get().strip()

        if video_choice == "320x240":
            video_output_filename = "320_30fps.mjpeg"
        else:
            video_output_filename = "288_30fps.mjpeg"
            
        if audio_format_choice == "mp3":
            audio_output_filename = "44100.mp3"
        else:
            audio_output_filename = "44100.aac"
            
        video_output_path = os.path.join(output_dir, video_output_filename)
        audio_output_path = os.path.join(output_dir, audio_output_filename)

        if os.path.exists(video_output_path) or os.path.exists(audio_output_path):
            msg = f"Output files for '{filename}' already exist. Do you want to overwrite?"
            if not messagebox.askyesno("Overwrite Confirmation", msg):
                self.log_message(f"\nSkipping '{filename}' as requested.")
                return

        self.log_message(f"\nProcessing: {filename}")

        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            self.log_message(f"Error creating directory {output_dir}: {e}")
            return
            
        # --- 1. Video Conversion ---
        if video_choice == "320x240":
            video_args = '-vf "scale=320:240:force_original_aspect_ratio=increase,crop=320:240" -q:v 8'
        else:
            video_args = '-vf "scale=288:240:force_original_aspect_ratio=increase,crop=288:240" -q:v 8'
        
        self.log_message(f"Starting video conversion ({video_choice})...")
        video_command = f'"{FFMPEG_EXE}" -i "{input_filepath}" {video_args} -y "{video_output_path}"'
        
        status = self.run_ffmpeg_command(video_command, filename)
        if status == 'success':
            self.log_message(f"Video successfully converted to {video_output_path}")
        else:
            shutil.rmtree(output_dir, ignore_errors=True)
            self.log_message(f"Cleaned up partial files for '{filename}'.")
            return

        # --- 2. Audio Conversion ---
        if audio_format_choice == "mp3":
            audio_codec_args = "-ab 32k"
        else:
            audio_codec_args = "-ab 24k"
        
        audio_filter_args = f'-af "loudnorm=i=-20:lra=10,volume={audio_volume_choice}"'
        
        self.log_message(f"Starting audio conversion ({audio_format_choice.upper()} at {audio_volume_choice})...")
        audio_command = f'"{FFMPEG_EXE}" -i "{input_filepath}" -vn -ar 44100 -ac 1 {audio_codec_args} {audio_filter_args} -y "{audio_output_path}"'

        status = self.run_ffmpeg_command(audio_command, filename)
        if status == 'success':
            self.log_message(f"Audio successfully converted to {audio_output_path}")
        else:
            shutil.rmtree(output_dir, ignore_errors=True)
            self.log_message(f"Cleaned up partial files for '{filename}'.")
            return


if __name__ == "__main__":
    # Check for ffmpeg executable before starting the GUI
    try:
        check_command = [FFMPEG_EXE, '-version']
        popen_kwargs = {'capture_output': True}
        if platform.system() == "Windows":
            popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        subprocess.run(check_command, check=True, **popen_kwargs)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showerror(
            "FFmpeg Not Found",
            f"Could not find or run '{FFMPEG_EXE}'.\n\nPlease make sure the FFmpeg executable is in the same directory as this script, or that it is in your system's PATH."
        )
        exit()

    main_root = tk.Tk()
    app = ConverterApp(main_root)
    main_root.mainloop()
