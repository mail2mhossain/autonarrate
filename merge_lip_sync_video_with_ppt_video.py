from moviepy import VideoFileClip, CompositeVideoClip

# 1. Load your two clips
ppt_clip     = VideoFileClip("What_is_Robot.mp4")
lipsync_clip = VideoFileClip("result_voice.mp4")

# 2. Resize/position the lip-sync window
#    e.g. make it 25% of the width and put it in the top-right corner
overlay = (
    lipsync_clip
      .resized(width=ppt_clip.w * 0.25)            # scale to 25% of PPT width
      .with_position(("right", "top"))             # top-right, with no margin
      .with_duration(lipsync_clip.duration)            # ensure same duration
)

# 3. Composite them
final = CompositeVideoClip([ppt_clip, overlay])

# 4. (Optional) If your lip-sync clip already _has_ the audio you want,
#    MoviePy will pick it up automatically.  Otherwise you can explicitly set:
# final = final.set_audio(lipsync_clip.audio)

# 5. Export
final.write_videofile(
    "What is Robot.mp4",
    fps=ppt_clip.fps,
    codec="libx264",
    audio_codec="aac",
    preset="medium",
    threads=4
)
