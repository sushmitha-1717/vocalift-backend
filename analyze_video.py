import sys
import json
import os
import cv2
import subprocess
import whisper
from collections import defaultdict

# ----------------------
# Extract audio using FFmpeg
# ----------------------
def extract_audio(video_path, audio_path="temp_audio.wav"):
    try:
        command = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return audio_path
    except Exception as e:
        print(json.dumps({"error": f"Audio extraction failed: {e}"}))
        sys.exit(1)

# ----------------------
# Analyze video for eye contact using OpenCV
# ----------------------
def analyze_eye_contact(video_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(video_path)

    frame_count = 0
    face_detected_frames = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            face_detected_frames += 1

    cap.release()
    return round((face_detected_frames / frame_count) * 100, 2) if frame_count > 0 else 0

# ----------------------
# Analyze audio and transcript
# ----------------------
def analyze_audio(video_path):
    import re
    transcript = ""
    pace_score = 0
    clarity_score = 0
    filler_words = ["um", "uh", "like", "you know", "so", "i mean", "okay", "actually", "basically"]
    transcript_words = []
    filler_word_counts = defaultdict(int)

    try:
        audio_file = extract_audio(video_path)

        model = whisper.load_model("medium.en")
        result = model.transcribe(audio_file, word_timestamps=True, verbose=False)
        transcript = result.get('text', '').strip()

        try:
            for segment in result.get('segments', []):
                for word_info in segment.get('words', []):
                    word = word_info['word'].strip().lower()
                    transcript_words.append(word)
                    if word in filler_words:
                        filler_word_counts[word] += 1
        except Exception as e:
            print("Fallback: Using plain transcript")
            text_lower = transcript.lower()
            # Extract words without punctuation
            transcript_words = re.findall(r'\b\w+\b', text_lower)
            for word in filler_words:
                filler_word_counts[word] = sum(1 for w in transcript_words if w == word)

        filler_total = sum(filler_word_counts.values())
        word_count = len(transcript_words)
        pace_score = min(100, word_count * 3)
        clarity_score = min(100, word_count * 2)

        if os.path.exists(audio_file):
            os.remove(audio_file)

    except Exception as e:
        transcript = "No speech detected."
        print(f"Transcript error: {e}")

    return transcript, dict(filler_word_counts), clarity_score, pace_score

# ----------------------
# Main Analysis Function
# ----------------------
def analyze_video(video_path):
    eye_contact_score = analyze_eye_contact(video_path)
    transcript, filler_word_counts, clarity_score, pace_score = analyze_audio(video_path)

    body_score = 80 if eye_contact_score > 50 else 60
    total_filler = sum(filler_word_counts.values())

    overallScore = round(
        (0.4 * eye_contact_score) +
        (0.2 * clarity_score) +
        (0.2 * body_score) +
        (0.2 * pace_score) -
        (total_filler * 2), 2
    )

    feedback = {
        "eyeContact": f"{eye_contact_score}%",
        "bodyPosture": "Good" if eye_contact_score > 70 else "Needs Improvement",
        "fillerWords": filler_word_counts,
        "clarity": round(clarity_score, 2),
        "pace": round(pace_score, 2),
        "transcript": transcript[:150] + "..." if transcript else "No speech detected.",
        "overallScore": max(0, overallScore)
    }
    return feedback

# ----------------------
# Run the script
# ----------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python analyze_video.py <video_path>"}))
        sys.exit(1)
    video_path = sys.argv[1]
    try:
        feedback = analyze_video(video_path)
        print(json.dumps(feedback))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
