import time
import warnings
from io import StringIO
from threading import Thread
from typing import BinaryIO, Union
from urllib.error import URLError

import torch
import whisper
from whisper.utils import ResultWriter, WriteJSON, WriteSRT, WriteTSV, WriteTXT, WriteVTT

from app.asr_models.asr_model import ASRModel
from app.config import CONFIG

# Suppress FP16 warning on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")


class OpenAIWhisperASR(ASRModel):

    def load_model(self):
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Force FP32 on CPU to avoid FP16 warning and potential issues
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                if torch.cuda.is_available():
                    self.model = whisper.load_model(name=CONFIG.MODEL_NAME, download_root=CONFIG.MODEL_PATH).cuda()
                else:
                    # On CPU, explicitly use FP32
                    self.model = whisper.load_model(name=CONFIG.MODEL_NAME, download_root=CONFIG.MODEL_PATH, device="cpu")
                    # Ensure model is in FP32
                    if hasattr(self.model, 'to'):
                        self.model = self.model.float()
                
                Thread(target=self.monitor_idleness, daemon=True).start()
                break
            except URLError as e:
                if attempt < max_retries - 1:
                    print(f"Failed to download model (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"\n{'='*80}")
                    print("ERROR: Failed to download Whisper model after multiple attempts.")
                    print("\nPossible solutions:")
                    print("1. Check your internet connection")
                    print("2. If using Docker, try configuring DNS:")
                    print("   docker run --dns 8.8.8.8 --dns 8.8.4.4 ...")
                    print("3. Pre-download the model and mount it as a volume:")
                    print(f"   - Model path: {CONFIG.MODEL_PATH}")
                    print(f"   - Model name: {CONFIG.MODEL_NAME}")
                    print("4. Use a cached model directory:")
                    print("   docker run -v /path/to/cache:/root/.cache ...")
                    print(f"{'='*80}\n")
                    raise

    def transcribe(
        self,
        audio,
        task: Union[str, None],
        language: Union[str, None],
        initial_prompt: Union[str, None],
        vad_filter: Union[bool, None],
        word_timestamps: Union[bool, None],
        options: Union[dict, None],
        output,
    ):
        self.last_activity_time = time.time()

        with self.model_lock:
            if self.model is None:
                self.load_model()

        options_dict = {"task": task}
        if language:
            options_dict["language"] = language
        if initial_prompt:
            options_dict["initial_prompt"] = initial_prompt
        if word_timestamps:
            options_dict["word_timestamps"] = word_timestamps
        with self.model_lock:
            result = self.model.transcribe(audio, **options_dict)

        output_file = StringIO()
        self.write_result(result, output_file, output)
        output_file.seek(0)

        return output_file

    def language_detection(self, audio):

        self.last_activity_time = time.time()

        with self.model_lock:
            if self.model is None:
                self.load_model()

        # load audio and pad/trim it to fit 30 seconds
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio, self.model.dims.n_mels).to(self.model.device)

        # detect the spoken language
        with self.model_lock:
            _, probs = self.model.detect_language(mel)
        detected_lang_code = max(probs, key=probs.get)

        return detected_lang_code, probs[max(probs)]

    def write_result(self, result: dict, file: BinaryIO, output: Union[str, None]):
        options = {"max_line_width": 1000, "max_line_count": 10, "highlight_words": False}
        if output == "srt":
            WriteSRT(ResultWriter).write_result(result, file=file, options=options)
        elif output == "vtt":
            WriteVTT(ResultWriter).write_result(result, file=file, options=options)
        elif output == "tsv":
            WriteTSV(ResultWriter).write_result(result, file=file, options=options)
        elif output == "json":
            WriteJSON(ResultWriter).write_result(result, file=file, options=options)
        else:
            WriteTXT(ResultWriter).write_result(result, file=file, options=options)
