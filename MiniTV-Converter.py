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
        self.root.geometry("600x850")
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

        # FPS Input (Moved above Quality)
        fps_frame = tk.Frame(video_options_frame)
        fps_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Label(fps_frame, text="FPS:").pack(side=tk.LEFT, padx=(18, 5))
        self.video_fps = tk.StringVar(value="30")
        tk.Entry(fps_frame, textvariable=self.video_fps, width=5).pack(side=tk.LEFT)
        tk.Label(fps_frame, text="(Note: 30 for 288, 24 for 320)").pack(side=tk.LEFT, padx=(5, 0))

        # Quality Input
        quality_frame = tk.Frame(video_options_frame)
        quality_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Label(quality_frame, text="Quality (0-51, lower is better):").pack(side=tk.LEFT, padx=(18, 5))
        self.video_quality = tk.StringVar(value="8")
        tk.Entry(quality_frame, textvariable=self.video_quality, width=5).pack(side=tk.LEFT)
        tk.Label(quality_frame, text="(Default: 8 but dont vary too much either side)").pack(side=tk.LEFT, padx=(5, 0))

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

        # Output Naming & Folder Options
        naming_frame = ttk.LabelFrame(self.options_frame, text="Output Naming & Folder Options", padding=(10, 5))
        naming_frame.pack(fill=tk.X, pady=5)

        self.naming_mode = tk.StringVar(value="legacy")
        tk.Radiobutton(naming_frame, text="Legacy Naming (e.g. 288_30fps.mjpeg & 44100.aac in subfolders)", variable=self.naming_mode, value="legacy", command=self.update_naming_state).pack(anchor='w')
        tk.Radiobutton(naming_frame, text="Match Original Filename (e.g. video.mjpeg & video.aac)", variable=self.naming_mode, value="match", command=self.update_naming_state).pack(anchor='w')

        self.folder_options_frame = tk.Frame(naming_frame)
        self.folder_options_frame.pack(fill=tk.X, padx=20, pady=(5, 0))
        
        self.folder_mode = tk.StringVar(value="subfolder")
        self.rb_subfolder = tk.Radiobutton(self.folder_options_frame, text="Output to a new subfolder for each file", variable=self.folder_mode, value="subfolder")
        self.rb_subfolder.pack(anchor='w')
        self.rb_samedir = tk.Radiobutton(self.folder_options_frame, text="Output all files into a 'Converted' folder", variable=self.folder_mode, value="same_dir")
        self.rb_samedir.pack(anchor='w')

        self.update_naming_state()

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

    def update_naming_state(self):
        """Enables or disables folder options based on naming mode."""
        if self.naming_mode.get() == "legacy":
            self.rb_subfolder.config(state=tk.DISABLED)
            self.rb_samedir.config(state=tk.DISABLED)
            self.folder_mode.set("subfolder")
        else:
            self.rb_subfolder.config(state=tk.NORMAL)
            self.rb_samedir.config(state=tk.NORMAL)

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
        """Validates inputs and starts the conversion threads."""
        # Validate Quality Input
        try:
            q_val = int(self.video_quality.get())
            if not (0 <= q_val <= 51):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Video Quality must be a number between 0 and 51.")
            return

        # Validate FPS Input
        try:
            fps_val = int(self.video_fps.get())
            if fps_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "FPS must be a positive number.")
            return

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
        """Requests to stop the conversion process after confirmation."""
        if messagebox.askyesno("Confirm Stop", "Are you sure you want to stop the conversion?\nThe current file will be cancelled immediately."):
            self.stop_requested = True
            self.log_message("\n--- STOP REQUESTED BY USER ---")
            if self.current_process:
                self.log_message(f"Forcefully terminating FFmpeg process (PID: {self.current_process.pid})...")
                try:
                    if platform.system() == "Windows":
                        subprocess.run(
                            f"taskkill /PID {self.current_process.pid} /F /T",
                            check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        os.kill(self.current_process.pid, 9)
                    self.log_message("Process terminated.")
                except (subprocess.CalledProcessError, OSError) as e:
                    self.log_message(f"Could not terminate process: {e}")
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
                messagebox.showinfo("Success", f"All video conversions are complete!\nTotal time: {duration_str}")

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
            self.log_message(f"An exception occurred: {e}")
            return 'error'
        finally:
            self.current_process = None

    def process_file(self, filename):
        """Processes a single video file based on the selected GUI options."""
        input_filepath = os.path.join(self.input_directory, filename)
        file_basename = os.path.splitext(filename)[0]
        
        v_res = self.video_option.get()
        a_fmt = self.audio_format.get()
        v_qual = self.video_quality.get()
        v_fps = self.video_fps.get().strip()
        a_vol = self.audio_volume.get().strip()
        naming = self.naming_mode.get()
        folder_setting = self.folder_mode.get()

        if naming == "legacy":
            v_out_name = f"{v_res.split('x')[0]}_{v_fps}fps.mjpeg"
            a_out_name = f"44100.{a_fmt}"
            output_dir = os.path.join(self.input_directory, file_basename)
        else:
            v_out_name = f"{file_basename}.mjpeg"
            a_out_name = f"{file_basename}.{a_fmt}"
            if folder_setting == "subfolder":
                output_dir = os.path.join(self.input_directory, file_basename)
            else:
                output_dir = os.path.join(self.input_directory, "Converted")
            
        v_path = os.path.join(output_dir, v_out_name)
        a_path = os.path.join(output_dir, a_out_name)

        if os.path.exists(v_path) or os.path.exists(a_path):
            if not messagebox.askyesno("Overwrite?", f"Files for {filename} exist. Overwrite?"):
                self.log_message(f"Skipping {filename}")
                return

        self.log_message(f"\nProcessing: {filename}")
        os.makedirs(output_dir, exist_ok=True)
            
        # --- 1. Video Conversion ---
        res_colon = v_res.replace('x', ':')
        vf = f"scale={res_colon}:force_original_aspect_ratio=increase,crop={res_colon},eq=brightness=-0.05"
        
        self.log_message(f"Starting video conversion ({v_res}, Quality: {v_qual}, FPS: {v_fps})...")
        v_cmd = f'"{FFMPEG_EXE}" -i "{input_filepath}" -vf "{vf}" -q:v {v_qual} -r {v_fps} -y "{v_path}"'
        
        status = self.run_ffmpeg_command(v_cmd, filename)
        if status != 'success':
            if not self.stop_requested: shutil.rmtree(output_dir, ignore_errors=True)
            return

        # --- 2. Audio Conversion ---
        codec = "-ab 32k" if a_fmt == "mp3" else "-ab 24k"
        af = f'loudnorm=i=-20:lra=10,volume={a_vol}'
        
        self.log_message(f"Starting audio conversion ({a_fmt.upper()})...")
        a_cmd = f'"{FFMPEG_EXE}" -i "{input_filepath}" -vn -ar 44100 -ac 1 {codec} -af "{af}" -y "{a_path}"'

        status = self.run_ffmpeg_command(a_cmd, filename)
        if status != 'success':
            if not self.stop_requested: shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    # Check for ffmpeg executable before starting the GUI
    try:
        check_command = [FFMPEG_EXE, '-version']
        popen_kwargs = {'capture_output': True}
        if platform.system() == "Windows":
            popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        subprocess.run(check_command, check=True, **popen_kwargs)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # We use a basic root for the error message since the app hasn't started
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showerror(
            "FFmpeg Not Found",
            f"Could not find or run '{FFMPEG_EXE}'.\n\nPlease ensure it is in the same folder as this script or in your PATH."
        )
        sys.exit()

    main_root = tk.Tk()
    app = ConverterApp(main_root)
    main_root.mainloop()
