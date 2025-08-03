

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import os
import shutil
import sys

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube ダウンローダー")
        self.root.geometry("550x350")

        self.ffmpeg_dir_path = None

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
        self.download_button.pack(pady=20)

        self.status_label = ttk.Label(root, text="初期化中...")
        self.status_label.pack(pady=5)

        # --- Initialization ---
        self.download_button.config(state="disabled")
        threading.Thread(target=self.setup_ffmpeg, daemon=True).start()

    def setup_ffmpeg(self):
        # 1. Check for existing ffmpeg
        ffmpeg_exe = shutil.which("ffmpeg")
        if ffmpeg_exe:
            self.ffmpeg_dir_path = os.path.dirname(ffmpeg_exe)
            self.root.after(0, self.update_status, "ffmpeg が見つかりました。準備完了です。")
            self.root.after(0, lambda: self.download_button.config(state="normal"))
            return

        # 2. If not found, ask to install via Winget
        self.root.after(0, self.install_ffmpeg_with_winget)

    def install_ffmpeg_with_winget(self):
        self.update_status("ffmpeg が見つかりません。")
        if messagebox.askyesno("ffmpeg インストール確認", "動画と音声を結合するために ffmpeg が必要です。\n\nWinget を使用して自動でインストールしますか？"):
            self.update_status("Winget で ffmpeg をインストールしています...")
            self.download_button.config(state="disabled")
            try:
                # This will open a new terminal for the installation
                command = "winget install --id=Gyan.FFmpeg -e"
                subprocess.Popen(command, shell=True)
                messagebox.showinfo("インストール実行中", f"ffmpeg のインストールを開始しました。\n\nインストールが完了したら、このアプリケーションを一度終了し、再度起動してください。")
                self.root.destroy() # Close the app after showing info
            except Exception as e:
                messagebox.showerror("Winget エラー", f"Winget の実行に失敗しました。Winget がインストールされているか確認してください。\nエラー: {e}")
                self.update_status("ffmpeg のインストールに失敗しました。")
        else:
            self.update_status("警告: ffmpeg がないため、動画・音声の変換に失敗する可能性があります。")
            self.download_button.config(state="normal")

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
        threading.Thread(target=self.download_thread, args=(url,), daemon=True).start()

    def download_thread(self, url):
        try:
            download_format = self.format_var.get()
            download_path = self.path_var.get()
            
            command = ["yt-dlp", "--no-mtime"]
            if self.ffmpeg_dir_path:
                 # Add ffmpeg to PATH for this process
                env = os.environ.copy()
                env["PATH"] = self.ffmpeg_dir_path + os.pathsep + env["PATH"]
            else:
                env = os.environ.copy()

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
                if output: self.root.after(0, self.update_status, output.strip())
            
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
        messagebox.showinfo("成功", "ダウンロードが正常に完了しました。")

    def download_error(self, error_message):
        self.status_label.config(text="ダウンロードに失敗しました。")
        self.download_button.config(state="normal")
        messagebox.showerror("エラー", f"エラーが発生しました:\n{error_message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
