import sys
import os
import time
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox,
    QSlider, QFrame, QProgressBar  
)
from custome_frame import RectFrame
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QSizePolicy
import vlc

from generate_video import (
    generate_audio_from_points,
    measure_durations,
    apply_point_timings,
    ppt_to_video,
    combine_audio,
    merge_audio_video
)

# Worker thread to run PowerPoint-to-video conversion without freezing the UI
class ConversionWorker(QThread):
    finished = Signal(str)       # Emitted with video path on success
    error = Signal(str)          # Emitted with error message on failure
    progress = Signal(int, str)  

    def __init__(self, ppt_path: str):
        super().__init__()
        self.ppt_path = ppt_path
        video_file_name = os.path.splitext(os.path.basename(self.ppt_path))[0]
        parent_dir = os.path.dirname(os.path.abspath(self.ppt_path))
        self.video_dir = os.path.join(parent_dir, video_file_name)
        
        if not os.path.exists(self.video_dir):
            os.makedirs(self.video_dir)

        self.video_path = os.path.join(self.video_dir, video_file_name + ".mp4")
        self.ppt_video_path = os.path.join(self.video_dir, video_file_name + "_ppt.mp4")
        self.audio_dir = os.path.join(self.video_dir, "audio")
        

    def run(self):
        try:
            self.progress.emit(0, "Starting audio generation...")
            audio_map = generate_audio_from_points(self.ppt_path, self.audio_dir, progress_callback=lambda p, m: self.progress.emit(p, "Audio: " + m))
            self.progress.emit(0, "Starting duration measurement...")
            durations_map = measure_durations(audio_map, progress_callback=lambda p, m: self.progress.emit(p, "Duration: " + m))
            
            self.progress.emit(0, "Starting point timing...")
            for attempt in range(3):
                try:
                    apply_point_timings(self.ppt_path, durations_map, progress_callback=lambda p, m: self.progress.emit(p, "Point timing: " + m))
                    break  # Success, exit the retry loop
                except Exception as e:
                    if attempt == 2:
                        self.error.emit(f"Video generation failed during point timing: {e}")
                        return  # Stop further processing
                    self.progress.emit(0, f"Retrying point timing due to error: {e} (attempt {attempt + 2}/3)")
            
            self.progress.emit(0, "Starting video generation...")
            if not os.path.exists(self.ppt_video_path):
                ppt_to_video(self.ppt_path, self.ppt_video_path, use_timings=True, default_slide_duration=7, progress_callback=lambda p, m: self.progress.emit(p, "Video: " + m))
            # combine generated audio and merge with video
            self.progress.emit(0, "Starting audio combination...")
            combined_audio_file = os.path.join(self.video_dir, "combined_audio.mp3")
            if not os.path.exists(combined_audio_file):
                combine_audio(audio_map,combined_audio_file, progress_callback=lambda p, m: self.progress.emit(p, "Audio: " + m))
            self.progress.emit(0, "Starting merge audio and video...")
            
            if not os.path.exists(self.video_path):
                merge_audio_video(self.ppt_video_path, combined_audio_file,  self.video_path, progress_callback=lambda p, m: self.progress.emit(p, "Merge: " + m))
                    
            self.progress.emit(100, "Done")
            # Notify success
            self.finished.emit(self.video_path)
        except Exception as e:
            # Notify error
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoNarrate")
        self.resize(800, 600)

        self.ppt_path = ""
        self.video_path = ""
        self.worker = None

        # Set up UI
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- Top Row: File path label and buttons ---
        top_row_frame = RectFrame()
        top_row_layout = QHBoxLayout(top_row_frame)
        top_row_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Qt.AlignLeft | Qt.AlignVCenter, Qt.AlignCenter
        top_row_layout.setContentsMargins(10, 10, 10, 10)
        self.file_label = QLabel("No file selected")
        self.file_button = QPushButton("Select PPTX")
        self.file_button.clicked.connect(self.select_ppt)
        self.generate_button = QPushButton("Generate Video")
        self.generate_button.clicked.connect(self.generate_video)
        top_row_layout.addWidget(self.file_label)
        top_row_layout.addWidget(self.file_button)
        top_row_layout.addWidget(self.generate_button)
        main_layout.addWidget(top_row_frame, 0)

        # --- Progress Frame: Progress message and bar ---
        progress_frame = RectFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setAlignment(Qt.AlignCenter)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        self.status_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addWidget(progress_frame, 0)

        # --- Video Frame Group: Video display and controls ---
        video_frame_group = RectFrame()
        video_layout = QVBoxLayout(video_frame_group)
        video_layout.setContentsMargins(10, 10, 10, 10)
        video_layout.setSpacing(0)

        width = video_frame_group.width()
        height = video_frame_group.height()

        # VLC video display area
        self.video_frame = QFrame()
        self.video_frame.setMinimumSize(width, height)
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame.setStyleSheet("background-color: black; border: 2px solid black;")

        self.video_frame.show()
        video_layout.addWidget(self.video_frame) # alignment=Qt.AlignLeft | Qt.AlignVCenter

        # Playback controls
        controls = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_video)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.sliderMoved.connect(self.set_position)
        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(QLabel("Volume:"))
        controls.addWidget(self.volume_slider)
        controls.addWidget(QLabel("Position:"))
        controls.addWidget(self.position_slider)

        for widget in (self.play_button, self.stop_button, self.volume_slider, self.position_slider):
            widget.hide()

        video_layout.addLayout(controls)
        main_layout.addWidget(video_frame_group, 1)  # Stretch factor 1 for video area

        self.setCentralWidget(central)

        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()
        self.media_player.set_hwnd(int(self.video_frame.winId()))

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)  # Update every 100ms
        self.update_timer.timeout.connect(self.update_ui)
        
    @Slot(int, str)
    def on_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    @Slot()
    def select_ppt(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select PPTX File", "", "PowerPoint Files (*.pptx)"
        )
        if file:
            self.ppt_path = file
            self.file_label.setText(os.path.basename(file))

    @Slot()
    def generate_video(self):
        if not self.ppt_path:
            QMessageBox.warning(self, "Warning", "Please select a PPTX file first.")
            return

        # Disable button to prevent re-entry
        self.generate_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Converting...")

        # Start conversion in background
        self.worker = ConversionWorker(self.ppt_path)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.start()

    @Slot(str)
    def on_conversion_finished(self, path: str):
        QMessageBox.information(self, "Success", f"Video generated: {path}")
        self.generate_button.setEnabled(True)

        # Load and show video player
        self.load_video(path)
        self.video_frame.show()
        self.play_button.show()
        self.stop_button.show()
        self.volume_slider.show()
        self.position_slider.show()
        self.update_timer.start()

    @Slot(str)
    def on_conversion_error(self, message: str):
        QMessageBox.critical(self, "Error", f"Conversion failed:\n{message}")
        self.generate_button.setEnabled(True)
        
    def load_video(self, path):
        # On Windows, need to convert path
        if sys.platform.startswith('win'):
            path = path.replace('\\', '/')
            
        # Create a media object and set it to the media player
        media = self.instance.media_new(path)
        self.media_player.set_media(media)
        self.media_player.set_hwnd(int(self.video_frame.winId()))
        
        # Set the video widget as the rendering window
        if sys.platform.startswith('win'):
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform.startswith('linux'):
            self.media_player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform.startswith('darwin'):
            self.media_player.set_nsobject(int(self.video_frame.winId()))
            
        # Set initial volume
        self.set_volume(self.volume_slider.value())

    @Slot()
    def toggle_play(self):
        if self.media_player.is_playing():
            self.media_player.pause()
            self.play_button.setText("Play")
        else:
            self.media_player.play()
            self.play_button.setText("Pause")

    @Slot()
    def stop_video(self):
        self.media_player.stop()
        self.play_button.setText("Play")
        
    @Slot(int)
    def set_volume(self, volume):
        self.media_player.audio_set_volume(volume)
        
    @Slot(int)
    def set_position(self, position):
        # Convert position slider value to VLC position (0.0 to 1.0)
        self.media_player.set_position(position / 1000.0)
        
    @Slot()
    def update_ui(self):
        # Update position slider
        if self.media_player.is_playing():
            position = int(self.media_player.get_position() * 1000)
            self.position_slider.setValue(position)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
