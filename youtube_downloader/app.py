

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import os
import shutil
import sys
import urllib.request
import zipfile

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube ダウンローダー")
        self.root.geometry("550x380") # Height increased for progress bar

        # Determine the base directory (especially for PyInstaller)
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.ffmpeg_dir_path = os.path.join(self.base_dir, "ffmpeg", "bin")

        # --- GUI Elements (Japanese) ---
        self.url_label = ttk.Label(root, text="YouTube URL:")
        self.url_label.pack(pady=5)
        self.url_entry = ttk.Entry(root, width=70)
        self.url_entry.pack(pady=5, padx=10)

        self.format_label = ttk.Label(root, text="フォーマット:")
        self.format_label.pack(pady=5)
        self.format_var = tk.StringVar(value="mp4-720p")
        self.format_menu = ttk.Combobox(
            root,
            textvariable=self.format_var,
            values=["mp3", "m4a", "wav", "mp4-1080p", "mp4-720p", "mp4-4k"],
            state="readonly"
        )
        self.format_menu.pack(pady=5)

        self.path_label = ttk.Label(root, text="ダウンロード先:")
        self.path_label.pack(pady=5)
        path_frame = ttk.Frame(root)
        path_frame.pack(pady=5, padx=10, fill=tk.X)
        self.path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=60, state="readonly")
        self.path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.browse_button = ttk.Button(path_frame, text="参照...", command=self.browse_path)
        self.browse_button.pack(side=tk.RIGHT, padx=(5,0))

        self.download_button = ttk.Button(root, text="ダウンロード", command=self.start_download)
        self.download_button.pack(pady=15)

        self.status_label = ttk.Label(root, text="初期化中...")
        self.status_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

        # --- Initialization ---
        self.download_button.config(state="disabled")
        threading.Thread(target=self.setup_ffmpeg, daemon=True).start()

    def setup_ffmpeg(self):
        if os.path.exists(os.path.join(self.ffmpeg_dir_path, "ffmpeg.exe")):
            self.root.after(0, self.update_status, "準備完了です。")
            self.root.after(0, lambda: self.download_button.config(state="normal"))
            return
        self.root.after(0, self.download_ffmpeg_prompt)

    def download_ffmpeg_prompt(self):
        self.update_status("ffmpeg が見つかりません。")
        if messagebox.askyesno("ffmpeg インストール確認", "動画と音声を結合するために ffmpeg が必要です。\n\n自動でダウンロードしてセットアップしますか？ (約80MB)"):
            threading.Thread(target=self.install_ffmpeg_thread, daemon=True).start()
        else:
            self.update_status("警告: ffmpeg がないため、処理に失敗する可能性があります。")
            self.download_button.config(state="normal")

    def install_ffmpeg_thread(self):
        try:
            self.root.after(0, self.update_status, "ffmpeg をダウンロードしています...")
            self.root.after(0, lambda: self.download_button.config(state="disabled"))
            ffmpeg_zip_path = os.path.join(self.base_dir, "ffmpeg.zip")
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            with urllib.request.urlopen(ffmpeg_url) as response, open(ffmpeg_zip_path, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk: break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        self.root.after(0, self.progress.config, {'value': progress})

            self.root.after(0, self.update_status, "ffmpeg を展開しています...")
            self.root.after(0, self.progress.config, {'value': 0})
            extract_dir = os.path.join(self.base_dir, "ffmpeg_temp")
            with zipfile.ZipFile(ffmpeg_zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            extracted_folder = os.path.join(extract_dir, os.listdir(extract_dir)[0])
            final_ffmpeg_dir = os.path.join(self.base_dir, "ffmpeg")
            shutil.move(extracted_folder, final_ffmpeg_dir)

            os.remove(ffmpeg_zip_path)
            shutil.rmtree(extract_dir)

            self.root.after(0, self.update_status, "ffmpeg の準備が完了しました。準備完了です。")
            self.root.after(0, lambda: self.download_button.config(state="normal"))

        except Exception as e:
            self.root.after(0, self.update_status, f"ffmpeg のインストールに失敗しました。")
            messagebox.showerror("エラー", f"ffmpeg のインストールに失敗しました: {e}")

    def browse_path(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("エラー", "YouTube の URL を入力してください。")
            return
        self.download_button.config(state="disabled")
        self.status_label.config(text="ダウンロードを開始しています...")
        self.progress['value'] = 0
        threading.Thread(target=self.download_thread, args=(url,), daemon=True).start()

    def download_thread(self, url):
        try:
            download_format = self.format_var.get()
            download_path = self.path_var.get()
            env = os.environ.copy()
            env["PATH"] = self.ffmpeg_dir_path + os.pathsep + env["PATH"]

            command = ["yt-dlp", "--no-mtime", "--progress"]
            if download_format in ["mp3", "m4a", "wav"]:
                command.extend(["-x", "--audio-format", download_format])
            else:
                format_map = {
                    "mp4-1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                    "mp4-720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
                    "mp4-4k": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]"
                }
                command.extend(["-f", format_map[download_format], "--merge-output-format", "mp4"])
            command.extend(["-o", f"{download_path}/%(title)s.%(ext)s", url])

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW, env=env)

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None: break
                if output:
                    self.root.after(0, self.update_status, output.strip())
                    if "[download]" in output:
                        parts = output.split()
                        try:
                            percentage_str = [p for p in parts if p.endswith('%')][0]
                            percentage = float(percentage_str[:-1])
                            self.root.after(0, self.progress.config, {'value': percentage})
                        except (IndexError, ValueError): pass
            
            stderr = process.communicate()[1]
            if process.returncode != 0:
                raise Exception(f"yt-dlp エラー: {stderr}")

            self.root.after(0, self.download_complete)
        except Exception as e:
            self.root.after(0, self.download_error, str(e))

    def update_status(self, message):
        self.status_label.config(text=message)

    def download_complete(self):
        self.status_label.config(text="ダウンロードが完了しました！")
        self.download_button.config(state="normal")
        self.progress['value'] = 100
        messagebox.showinfo("成功", "ダウンロードが正常に完了しました。")

    def download_error(self, error_message):
        self.status_label.config(text="ダウンロードに失敗しました。")
        self.download_button.config(state="normal")
        messagebox.showerror("エラー", f"エラーが発生しました:\n{error_message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()

