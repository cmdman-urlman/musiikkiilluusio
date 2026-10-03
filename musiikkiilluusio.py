import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import math
import random

import numpy as np
import sounddevice as sd


# ============================================================
# SETTINGS
# ============================================================

RATE = 48000
BLOCK = 256

SPEED_OF_SOUND = 343.0
EAR_DISTANCE = 0.175

MAX_DISTANCE = 20.0
MAX_VOLUME = 80.0

SCALE = 70
ANIMATION_FPS = 40

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


# ============================================================
# COLORS
# ============================================================

BG = "#101216"
PANEL = "#181b21"
PANEL2 = "#20242b"
GRID = "#292e36"

TEXT = "#f1f3f5"
MUTED = "#8f98a5"

ACCENT = "#5aa9ff"
GREEN = "#5bd68a"
RED = "#ff6b6b"
YELLOW = "#ffd166"


# ============================================================
# AUDIO STATE
# ============================================================

audio = None
audio_pos = 0

stream = None

playing = False
file_name = ""

playback_mode = "Once"

audio_lock = threading.Lock()


# ============================================================
# SPATIAL POSITION
# ============================================================

speaker_x = 2.0
speaker_y = 2.0


# ============================================================
# AUDIO VOLUME
# ============================================================

volume = 70.0


# ============================================================
# DELAY HISTORY
# ============================================================

left_history = np.zeros(100, dtype=np.float32)
right_history = np.zeros(100, dtype=np.float32)


# ============================================================
# ANIMATION
# ============================================================

animation_name = "Manuaalinen"
animation_time = 0.0
animation_speed = 1.0
animation_running = False

custom_orbit_distance = 3.0


# ============================================================
# MOUSE
# ============================================================

dragging = False


# ============================================================
# ROOT
# ============================================================

root = tk.Tk()

root.title("Spatial Audio Lab")
root.geometry(
    f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
)

root.minsize(
    1000,
    700
)

root.configure(
    bg=BG
)


# ============================================================
# AUDIO FUNCTIONS
# ============================================================

def volume_gain(db_value):
    """
    Converts the 0-80 UI scale into a normal linear gain.

    80 = 1.0
    70 = ~0.316
    60 = 0.1
    etc.
    """

    db_value = max(
        0.0,
        min(
            MAX_VOLUME,
            db_value
        )
    )

    return 10 ** (
        (db_value - 80.0) / 20.0
    )


def load_audio(path):
    """
    Decode almost any common audio format through FFmpeg.
    Output:
        mono
        float32
        48000 Hz
    """

    global audio
    global audio_pos
    global file_name
    global left_history
    global right_history

    try:

        command = [
            "ffmpeg",

            "-v",
            "error",

            "-i",
            path,

            "-f",
            "f32le",

            "-ac",
            "1",

            "-ar",
            str(RATE),

            "pipe:1"
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:

            error_text = (
                result.stderr
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

            raise RuntimeError(
                error_text
            )

        data = np.frombuffer(
            result.stdout,
            dtype=np.float32
        )

        if len(data) == 0:

            raise RuntimeError(
                "Audio-tiedosto oli tyhjä."
            )

        with audio_lock:

            audio = data
            audio_pos = 0
            file_name = path

            left_history = np.zeros(
                100,
                dtype=np.float32
            )

            right_history = np.zeros(
                100,
                dtype=np.float32
            )

        update_file_label()

        update_status(
            "Ladattu"
        )

        return True

    except Exception as e:

        messagebox.showerror(
            "Audio error",
            str(e)
        )

        return False


def callback(outdata, frames, time_info, status):

    global audio_pos
    global playing
    global audio

    global left_history
    global right_history

    if status:

        pass

    outdata.fill(0)

    with audio_lock:

        if audio is None:
            return

        if not playing:
            return

        remaining = (
            len(audio) -
            audio_pos
        )

        if remaining <= 0:

            if playback_mode == "Repeat":

                audio_pos = 0

            else:

                playing = False

                root.after(
                    0,
                    update_play_button
                )

                root.after(
                    0,
                    update_status,
                    "Valmis"
                )

                return

        frames_to_read = min(
            frames,
            len(audio) - audio_pos
        )

        if frames_to_read <= 0:
            return

        source = audio[
            audio_pos:
            audio_pos + frames_to_read
        ].copy()

        audio_pos += frames_to_read

    # --------------------------------------------------------
    # SPATIAL PARAMETERS
    # --------------------------------------------------------

    (
        left_gain,
        right_gain,
        left_delay,
        right_delay,
        distance_gain
    ) = calculate_spatial()

    source *= distance_gain

    # --------------------------------------------------------
    # DELAY
    # --------------------------------------------------------

    left = np.zeros(
        frames_to_read,
        dtype=np.float32
    )

    right = np.zeros(
        frames_to_read,
        dtype=np.float32
    )

    left, left_history = delay_signal(
        source,
        left_delay,
        left_history
    )

    right, right_history = delay_signal(
        source,
        right_delay,
        right_history
    )

    left *= left_gain
    right *= right_gain

    # --------------------------------------------------------
    # MASTER VOLUME
    # --------------------------------------------------------

    master = volume_gain(
        volume
    )

    left *= master
    right *= master

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output = np.zeros(
        (
            frames,
            2
        ),
        dtype=np.float32
    )

    output[
        :frames_to_read,
        0
    ] = left

    output[
        :frames_to_read,
        1
    ] = right

    output = np.clip(
        output,
        -1.0,
        1.0
    )

    outdata[:] = output


def delay_signal(
    signal,
    delay_samples,
    history
):

    delay_samples = int(
        max(
            0,
            delay_samples
        )
    )

    if delay_samples == 0:

        return (
            signal,
            signal[-100:].copy()
        )

    combined = np.concatenate(
        (
            history,
            signal
        )
    )

    start = (
        len(history) -
        delay_samples
    )

    end = (
        start +
        len(signal)
    )

    if start < 0:

        pad = np.zeros(
            -start,
            dtype=np.float32
        )

        combined = np.concatenate(
            (
                pad,
                combined
            )
        )

        start = 0
        end = len(signal)

    delayed = combined[
        start:end
    ]

    if len(delayed) < len(signal):

        delayed = np.pad(
            delayed,
            (
                0,
                len(signal) -
                len(delayed)
            )
        )

    new_history = np.concatenate(
        (
            history,
            signal
        )
    )[-100:]

    return (
        delayed.astype(
            np.float32
        ),
        new_history
    )


# ============================================================
# SPATIAL AUDIO
# ============================================================

def calculate_spatial():

    x = speaker_x
    y = speaker_y

    distance = math.sqrt(
        x * x +
        y * y
    )

    distance = max(
        distance,
        0.05
    )

    # --------------------------------------------------------
    # EAR POSITIONS
    # --------------------------------------------------------

    left_ear_x = -EAR_DISTANCE / 2
    right_ear_x = EAR_DISTANCE / 2

    left_distance = math.sqrt(
        (x - left_ear_x) ** 2 +
        y ** 2
    )

    right_distance = math.sqrt(
        (x - right_ear_x) ** 2 +
        y ** 2
    )

    # --------------------------------------------------------
    # ITD
    # --------------------------------------------------------

    distance_difference = (
        right_distance -
        left_distance
    )

    itd_seconds = (
        distance_difference /
        SPEED_OF_SOUND
    )

    max_delay = 48

    if itd_seconds > 0:

        left_delay = int(
            min(
                max_delay,
                abs(itd_seconds) * RATE
            )
        )

        right_delay = 0

    else:

        left_delay = 0

        right_delay = int(
            min(
                max_delay,
                abs(itd_seconds) * RATE
            )
        )

    # --------------------------------------------------------
    # ANGLE
    #
    # 0   = front
    # 90  = right
    # 180 = back
    # -90 = left
    # --------------------------------------------------------

    angle = math.atan2(
        x,
        y
    )

    pan = math.sin(
        angle
    )

    pan_strength = 0.90

    effective_pan = (
        pan *
        pan_strength
    )

    # --------------------------------------------------------
    # EQUAL-POWER PANNING
    # --------------------------------------------------------

    left_pan = math.sqrt(
        max(
            0.0,
            1.0 - effective_pan
        )
    )

    right_pan = math.sqrt(
        max(
            0.0,
            1.0 + effective_pan
        )
    )

    left_pan = min(
        left_pan,
        1.0
    )

    right_pan = min(
        right_pan,
        1.0
    )

    # --------------------------------------------------------
    # HEAD SHADOW
    # --------------------------------------------------------

    side = abs(
        pan
    )

    shadow_db = (
        12.0 *
        side
    )

    shadow = 10 ** (
        -shadow_db / 20.0
    )

    if x > 0:

        left_pan *= shadow

    elif x < 0:

        right_pan *= shadow

    # --------------------------------------------------------
    # DISTANCE ATTENUATION
    # --------------------------------------------------------

    distance_gain = 1.0 / max(
        1.0,
        distance
    )

    return (
        left_pan,
        right_pan,
        left_delay,
        right_delay,
        distance_gain
    )


# ============================================================
# AUDIO START / STOP
# ============================================================

def start_audio():

    global stream
    global playing

    if audio is None:

        messagebox.showinfo(
            "Spatial Audio Lab",
            "Lataa ensin audio."
        )

        return

    try:

        if stream is None:

            stream = sd.OutputStream(
                samplerate=RATE,
                channels=2,
                dtype="float32",
                blocksize=BLOCK,
                callback=callback
            )

            stream.start()

        playing = True

        update_play_button()

        update_status(
            "Toistaa"
        )

    except Exception as e:

        messagebox.showerror(
            "Audio device error",
            str(e)
        )


def play_pause():

    global playing

    if audio is None:

        messagebox.showinfo(
            "Spatial Audio Lab",
            "Lataa ensin audio."
        )

        return

    if playing:

        playing = False

        update_status(
            "Tauko"
        )

    else:

        start_audio()

    update_play_button()


def stop_audio():

    global playing
    global audio_pos

    playing = False

    with audio_lock:

        audio_pos = 0

    update_play_button()

    update_status(
        "Pysäytetty"
    )


def close_audio():

    global stream

    try:

        if stream is not None:

            stream.stop()
            stream.close()

            stream = None

    except Exception:
        pass

    root.destroy()


# ============================================================
# PLAYBACK MODE
# ============================================================

def playback_mode_changed(event=None):

    global playback_mode

    playback_mode = (
        playback_mode_var.get()
    )

    update_status(
        playback_mode
    )


# ============================================================
# FILE
# ============================================================

def choose_file():

    path = filedialog.askopenfilename(
        title="Valitse audio",
        filetypes=[
            (
                "Audio files",
                "*.mp3 *.wav *.flac *.ogg "
                "*.m4a *.aac *.opus"
            ),
            (
                "All files",
                "*.*"
            )
        ]
    )

    if not path:
        return

    load_audio(
        path
    )


def update_file_label():

    if file_name:

        name = file_name.replace(
            "\\",
            "/"
        ).split("/")[-1]

        file_label.config(
            text=name
        )

    else:

        file_label.config(
            text="Ei tiedostoa"
        )


# ============================================================
# POSITION
# ============================================================

def update_position_from_fields(
    event=None
):

    global speaker_x
    global speaker_y

    try:

        distance = float(
            distance_entry.get()
        )

        angle_deg = float(
            angle_entry.get()
        )

        distance = max(
            0.05,
            min(
                MAX_DISTANCE,
                distance
            )
        )

        angle_deg = (
            (
                angle_deg + 180
            ) % 360
        ) - 180

        angle = math.radians(
            angle_deg
        )

        speaker_x = (
            distance *
            math.sin(angle)
        )

        speaker_y = (
            distance *
            math.cos(angle)
        )

        update_canvas()

    except ValueError:

        pass


def update_fields_from_position():

    distance = math.sqrt(
        speaker_x ** 2 +
        speaker_y ** 2
    )

    angle = math.degrees(
        math.atan2(
            speaker_x,
            speaker_y
        )
    )

    distance_entry.delete(
        0,
        tk.END
    )

    distance_entry.insert(
        0,
        f"{distance:.2f}"
    )

    angle_entry.delete(
        0,
        tk.END
    )

    angle_entry.insert(
        0,
        f"{angle:.1f}"
    )


# ============================================================
# ANIMATION
# ============================================================

ANIMATIONS = [
    "Manuaalinen",
    "Orbit 1 m",
    "Orbit 2 m",
    "Orbit 5 m",
    "Orbit 10 m",
    "Orbit Custom",
    "Vasen → Oikea",
    "Eteen → Taakse",
    "Kahdeksikko",
    "Satunnainen"
]


def get_animation_position(t):

    name = animation_var.get()

    # --------------------------------------------------------
    # MANUAL
    # --------------------------------------------------------

    if name == "Manuaalinen":

        return (
            speaker_x,
            speaker_y
        )

    # --------------------------------------------------------
    # ORBIT
    # --------------------------------------------------------

    if name == "Orbit 1 m":

        radius = 1.0

        angle = (
            t *
            2.0 *
            math.pi /
            8.0
        )

        return (
            radius * math.sin(angle),
            radius * math.cos(angle)
        )

    if name == "Orbit 2 m":

        radius = 2.0

        angle = (
            t *
            2.0 *
            math.pi /
            8.0
        )

        return (
            radius * math.sin(angle),
            radius * math.cos(angle)
        )

    if name == "Orbit 5 m":

        radius = 5.0

        angle = (
            t *
            2.0 *
            math.pi /
            8.0
        )

        return (
            radius * math.sin(angle),
            radius * math.cos(angle)
        )

    if name == "Orbit 10 m":

        radius = 10.0

        angle = (
            t *
            2.0 *
            math.pi /
            8.0
        )

        return (
            radius * math.sin(angle),
            radius * math.cos(angle)
        )

    if name == "Orbit Custom":

        radius = max(
            0.05,
            min(
                MAX_DISTANCE,
                custom_orbit_distance
            )
        )

        angle = (
            t *
            2.0 *
            math.pi /
            8.0
        )

        return (
            radius * math.sin(angle),
            radius * math.cos(angle)
        )

    # --------------------------------------------------------
    # LEFT → RIGHT
    # --------------------------------------------------------

    if name == "Vasen → Oikea":

        phase = (
            math.sin(
                t * 0.5
            )
            + 1.0
        ) / 2.0

        x = (
            -5.0 +
            phase * 10.0
        )

        return (
            x,
            0.0
        )

    # --------------------------------------------------------
    # FRONT → BACK
    # --------------------------------------------------------

    if name == "Eteen → Taakse":

        phase = (
            math.sin(
                t * 0.35
            )
            + 1.0
        ) / 2.0

        y = (
            5.0 -
            phase * 10.0
        )

        return (
            0.0,
            y
        )

    # --------------------------------------------------------
    # FIGURE EIGHT
    # --------------------------------------------------------

    if name == "Kahdeksikko":

        x = (
            5.0 *
            math.sin(
                t * 0.5
            )
        )

        y = (
            3.0 *
            math.sin(
                t
        )
            * math.cos(
                t * 0.5
            )
        )

        return (
            x,
            y
        )

    # --------------------------------------------------------
    # RANDOM
    # --------------------------------------------------------

    if name == "Satunnainen":

        if (
            int(t * 0.5)
            !=
            int(
                (t - 1 / ANIMATION_FPS)
                * 0.5
            )
        ):

            radius = random.uniform(
                1.0,
                8.0
            )

            angle = random.uniform(
                -math.pi,
                math.pi
            )

            random_animation_position[0] = (
                radius *
                math.sin(angle)
            )

            random_animation_position[1] = (
                radius *
                math.cos(angle)
            )

        return (
            random_animation_position[0],
            random_animation_position[1]
        )

    return (
        speaker_x,
        speaker_y
    )


random_animation_position = [
    3.0,
    3.0
]


def animation_changed(event=None):

    global animation_name

    animation_name = (
        animation_var.get()
    )

    if animation_name == "Manuaalinen":

        set_animation_state(
            False
        )

    else:

        set_animation_state(
            True
        )


def set_animation_state(enabled):

    global animation_running

    animation_running = enabled

    if enabled:

        animation_status.config(
            text="● ANIMAATIO",
            fg=GREEN
        )

    else:

        animation_status.config(
            text="● MANUAALINEN",
            fg=MUTED
        )


def animation_speed_changed(
    value
):

    global animation_speed

    try:

        animation_speed = float(
            value
        )

        animation_speed = max(
            0.05,
            min(
                20.0,
                animation_speed
            )
        )

        animation_speed_entry.delete(
            0,
            tk.END
        )

        animation_speed_entry.insert(
            0,
            f"{animation_speed:.2f}"
        )

    except ValueError:

        pass


def animation_speed_entry_changed(
    event=None
):

    global animation_speed

    try:

        value = float(
            animation_speed_entry.get()
        )

        animation_speed = max(
            0.05,
            min(
                20.0,
                value
            )
        )

        animation_speed_entry.delete(
            0,
            tk.END
        )

        animation_speed_entry.insert(
            0,
            f"{animation_speed:.2f}"
        )

        animation_speed_slider.set(
            animation_speed
        )

    except ValueError:

        animation_speed_entry.delete(
            0,
            tk.END
        )

        animation_speed_entry.insert(
            0,
            f"{animation_speed:.2f}"
        )


def custom_orbit_changed(
    event=None
):

    global custom_orbit_distance

    try:

        custom_orbit_distance = float(
            custom_orbit_entry.get()
        )

        custom_orbit_distance = max(
            0.05,
            min(
                MAX_DISTANCE,
                custom_orbit_distance
            )
        )

    except ValueError:

        pass


def animation_loop():

    global animation_time
    global speaker_x
    global speaker_y

    if animation_running:

        animation_time += (
            animation_speed /
            ANIMATION_FPS
        )

        x, y = get_animation_position(
            animation_time
        )

        speaker_x = x
        speaker_y = y

        update_fields_from_position()
        update_canvas()

    root.after(
        int(
            1000 /
            ANIMATION_FPS
        ),
        animation_loop
    )


# ============================================================
# MOUSE DRAG
# ============================================================

def world_to_screen(
    x,
    y
):

    cx = canvas.winfo_width() / 2
    cy = canvas.winfo_height() / 2

    return (
        cx + x * SCALE,
        cy - y * SCALE
    )


def screen_to_world(
    sx,
    sy
):

    cx = canvas.winfo_width() / 2
    cy = canvas.winfo_height() / 2

    return (
        (sx - cx) / SCALE,
        -(sy - cy) / SCALE
    )


def mouse_down(event):

    global dragging

    sx, sy = world_to_screen(
        speaker_x,
        speaker_y
    )

    distance = math.sqrt(
        (event.x - sx) ** 2 +
        (event.y - sy) ** 2
    )

    if distance < 45:

        dragging = True

        set_animation_state(
            False
        )

        animation_var.set(
            "Manuaalinen"
        )

        animation_changed()


def mouse_move(event):

    global speaker_x
    global speaker_y

    if not dragging:
        return

    x, y = screen_to_world(
        event.x,
        event.y
    )

    distance = math.sqrt(
        x * x +
        y * y
    )

    if distance > MAX_DISTANCE:

        scale = (
            MAX_DISTANCE /
            distance
        )

        x *= scale
        y *= scale

    speaker_x = x
    speaker_y = y

    update_fields_from_position()
    update_canvas()


def mouse_up(event):

    global dragging

    dragging = False


# ============================================================
# CANVAS
# ============================================================

def update_canvas():

    canvas.delete(
        "all"
    )

    width = canvas.winfo_width()
    height = canvas.winfo_height()

    cx = width / 2
    cy = height / 2

    # --------------------------------------------------------
    # GRID
    # --------------------------------------------------------

    grid_range = int(
        MAX_DISTANCE
    )

    for i in range(
        -grid_range,
        grid_range + 1
    ):

        x = cx + i * SCALE

        canvas.create_line(
            x,
            0,
            x,
            height,
            fill=GRID
        )

        y = cy - i * SCALE

        canvas.create_line(
            0,
            y,
            width,
            y,
            fill=GRID
        )

    # --------------------------------------------------------
    # AXES
    # --------------------------------------------------------

    canvas.create_line(
        cx,
        0,
        cx,
        height,
        fill="#3a404a"
    )

    canvas.create_line(
        0,
        cy,
        width,
        cy,
        fill="#3a404a"
    )

    # --------------------------------------------------------
    # DISTANCE CIRCLES
    # --------------------------------------------------------

    for radius in (
        1,
        2,
        5,
        10
    ):

        r = radius * SCALE

        canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline=GRID
        )

        canvas.create_text(
            cx + 5,
            cy - r - 8,
            text=f"{radius} m",
            fill=MUTED,
            anchor="w"
        )

    # --------------------------------------------------------
    # PERSON
    # --------------------------------------------------------

    person_x = cx
    person_y = cy

    canvas.create_oval(
        person_x - 18,
        person_y - 28,
        person_x + 18,
        person_y + 8,
        fill=ACCENT,
        outline=""
    )

    canvas.create_oval(
        person_x - 9,
        person_y - 38,
        person_x + 9,
        person_y - 20,
        fill=ACCENT,
        outline=""
    )

    canvas.create_line(
        person_x - 28,
        person_y + 35,
        person_x,
        person_y + 5,
        fill=ACCENT,
        width=6
    )

    canvas.create_line(
        person_x + 28,
        person_y + 35,
        person_x,
        person_y + 5,
        fill=ACCENT,
        width=6
    )

    # --------------------------------------------------------
    # FRONT INDICATOR
    # --------------------------------------------------------

    canvas.create_text(
        cx,
        cy - 65,
        text="FRONT",
        fill=MUTED,
        font=("Segoe UI", 9)
    )

    canvas.create_text(
        cx,
        cy + 65,
        text="BACK",
        fill=MUTED,
        font=("Segoe UI", 9)
    )

    # --------------------------------------------------------
    # SPEAKER
    # --------------------------------------------------------

    sx, sy = world_to_screen(
        speaker_x,
        speaker_y
    )

    # Connection line

    canvas.create_line(
        cx,
        cy,
        sx,
        sy,
        fill=ACCENT,
        dash=(4, 5),
        width=2
    )

    # Speaker pair

    speaker_size = 26

    canvas.create_rectangle(
        sx - 35,
        sy - 20,
        sx - 8,
        sy + 20,
        fill=PANEL2,
        outline=GREEN,
        width=2
    )

    canvas.create_rectangle(
        sx + 8,
        sy - 20,
        sx + 35,
        sy + 20,
        fill=PANEL2,
        outline=GREEN,
        width=2
    )

    canvas.create_oval(
        sx - 28,
        sy - 8,
        sx - 15,
        sy + 8,
        fill=GREEN,
        outline=""
    )

    canvas.create_oval(
        sx + 15,
        sy - 8,
        sx + 28,
        sy + 8,
        fill=GREEN,
        outline=""
    )

    # --------------------------------------------------------
    # SPEAKER LABEL
    # --------------------------------------------------------

    distance = math.sqrt(
        speaker_x ** 2 +
        speaker_y ** 2
    )

    angle = math.degrees(
        math.atan2(
            speaker_x,
            speaker_y
        )
    )

    canvas.create_text(
        sx,
        sy + 42,
        text=(
            f"{distance:.2f} m   "
            f"{angle:.1f}°"
        ),
        fill=TEXT,
        font=("Consolas", 10)
    )


# ============================================================
# INFO UPDATE
# ============================================================

def update_info():

    distance = math.sqrt(
        speaker_x ** 2 +
        speaker_y ** 2
    )

    angle = math.degrees(
        math.atan2(
            speaker_x,
            speaker_y
        )
    )

    (
        left_gain,
        right_gain,
        left_delay,
        right_delay,
        distance_gain
    ) = calculate_spatial()

    itd = abs(
        left_delay -
        right_delay
    )

    distance_value.config(
        text=f"{distance:.2f} m"
    )

    angle_value.config(
        text=f"{angle:.1f}°"
    )

    itd_value.config(
        text=f"{itd} samples"
    )

    left_value.config(
        text=f"{left_gain:.2f}"
    )

    right_value.config(
        text=f"{right_gain:.2f}"
    )

    attenuation_value.config(
        text=f"{distance_gain:.3f}"
    )


def information_loop():

    update_info()

    root.after(
        100,
        information_loop
    )


# ============================================================
# UI HELPERS
# ============================================================

def panel_title(
    parent,
    text
):

    tk.Label(
        parent,
        text=text,
        bg=PANEL,
        fg=MUTED,
        font=(
            "Segoe UI",
            9,
            "bold"
        ),
        anchor="w"
    ).pack(
        fill="x",
        padx=18,
        pady=(
            12,
            6
        )
    )


def update_play_button():

    if playing:

        play_button.config(
            text="❚❚  PAUSE"
        )

    else:

        play_button.config(
            text="▶  PLAY"
        )


def update_status(text):

    status_label.config(
        text=text
    )


# ============================================================
# TOP BAR
# ============================================================

top = tk.Frame(
    root,
    bg=PANEL,
    height=65
)

top.pack(
    fill="x"
)

top.pack_propagate(
    False
)


title = tk.Label(
    top,
    text="SPATIAL AUDIO LAB",
    bg=PANEL,
    fg=TEXT,
    font=(
        "Segoe UI",
        17,
        "bold"
    )
)

title.pack(
    side="left",
    padx=20
)


file_label = tk.Label(
    top,
    text="Ei tiedostoa",
    bg=PANEL,
    fg=MUTED,
    font=(
        "Segoe UI",
        10
    )
)

file_label.pack(
    side="left",
    padx=10
)


open_button = tk.Button(
    top,
    text="OPEN AUDIO",
    command=choose_file,
    bg=ACCENT,
    fg="white",
    activebackground=ACCENT,
    activeforeground="white",
    relief="flat",
    padx=18,
    pady=8,
    font=(
        "Segoe UI",
        9,
        "bold"
    )
)

open_button.pack(
    side="right",
    padx=20
)


# ============================================================
# MAIN AREA
# ============================================================

main = tk.Frame(
    root,
    bg=BG
)

main.pack(
    fill="both",
    expand=True
)


# ============================================================
# LEFT PANEL
# ============================================================

control = tk.Frame(
    main,
    bg=PANEL,
    width=310
)

control.pack(
    side="left",
    fill="y"
)

control.pack_propagate(
    False
)


# ============================================================
# PLAYBACK
# ============================================================

panel_title(
    control,
    "PLAYBACK"
)


play_button = tk.Button(
    control,
    text="▶  PLAY",
    command=play_pause,
    bg=GREEN,
    fg="#07120c",
    activebackground=GREEN,
    relief="flat",
    font=(
        "Segoe UI",
        10,
        "bold"
    ),
    height=2
)

play_button.pack(
    fill="x",
    padx=18,
    pady=4
)


stop_button = tk.Button(
    control,
    text="■  STOP",
    command=stop_audio,
    bg=PANEL2,
    fg=TEXT,
    activebackground="#2a3038",
    activeforeground=TEXT,
    relief="flat",
    font=(
        "Segoe UI",
        10
    ),
    height=2
)

stop_button.pack(
    fill="x",
    padx=18,
    pady=4
)


playback_mode_var = tk.StringVar(
    value="Once"
)


playback_mode_menu = tk.OptionMenu(
    control,
    playback_mode_var,
    "Once",
    "Repeat",
    command=playback_mode_changed
)

playback_mode_menu.config(
    bg=PANEL2,
    fg=TEXT,
    activebackground=PANEL2,
    activeforeground=TEXT,
    highlightthickness=0,
    relief="flat",
    font=(
        "Segoe UI",
        10
    )
)

playback_mode_menu["menu"].config(
    bg=PANEL2,
    fg=TEXT
)

playback_mode_menu.pack(
    fill="x",
    padx=18,
    pady=5
)


# ============================================================
# VOLUME
# ============================================================

panel_title(
    control,
    "VOLUME"
)


volume_frame = tk.Frame(
    control,
    bg=PANEL
)

volume_frame.pack(
    fill="x",
    padx=18
)


volume_entry = tk.Entry(
    volume_frame,
    width=7,
    bg=PANEL2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    justify="center",
    font=(
        "Consolas",
        11
    )
)

volume_entry.insert(
    0,
    "70"
)

volume_entry.pack(
    side="left"
)


tk.Label(
    volume_frame,
    text=" / 80",
    bg=PANEL,
    fg=MUTED
).pack(
    side="left"
)


def set_volume(value):

    global volume

    try:

        volume = float(
            value
        )

        volume = max(
            0.0,
            min(
                MAX_VOLUME,
                volume
            )
        )

        volume_entry.delete(
            0,
            tk.END
        )

        volume_entry.insert(
            0,
            f"{volume:.0f}"
        )

    except ValueError:

        pass


volume_slider = tk.Scale(
    control,
    from_=0,
    to=80,
    resolution=1,
    orient="horizontal",
    command=set_volume,
    bg=PANEL,
    fg=TEXT,
    troughcolor=PANEL2,
    highlightthickness=0,
    showvalue=False,
    length=250
)

volume_slider.set(
    70
)

volume_slider.pack(
    padx=15,
    pady=8
)


def volume_entry_changed(
    event=None
):

    global volume

    try:

        volume = float(
            volume_entry.get()
        )

        volume = max(
            0.0,
            min(
                MAX_VOLUME,
                volume
            )
        )

        volume_slider.set(
            volume
        )

        volume_entry.delete(
            0,
            tk.END
        )

        volume_entry.insert(
            0,
            f"{volume:.0f}"
        )

    except ValueError:
        pass


volume_entry.bind(
    "<Return>",
    volume_entry_changed
)

volume_entry.bind(
    "<FocusOut>",
    volume_entry_changed
)


# ============================================================
# POSITION
# ============================================================

panel_title(
    control,
    "POSITION"
)


distance_frame = tk.Frame(
    control,
    bg=PANEL
)

distance_frame.pack(
    fill="x",
    padx=18,
    pady=3
)


tk.Label(
    distance_frame,
    text="Distance",
    bg=PANEL,
    fg=MUTED,
    width=10,
    anchor="w"
).pack(
    side="left"
)


distance_entry = tk.Entry(
    distance_frame,
    width=8,
    bg=PANEL2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    justify="center"
)

distance_entry.insert(
    0,
    "2.83"
)

distance_entry.pack(
    side="left"
)

tk.Label(
    distance_frame,
    text=" m",
    bg=PANEL,
    fg=MUTED
).pack(
    side="left"
)


angle_frame = tk.Frame(
    control,
    bg=PANEL
)

angle_frame.pack(
    fill="x",
    padx=18,
    pady=3
)


tk.Label(
    angle_frame,
    text="Angle",
    bg=PANEL,
    fg=MUTED,
    width=10,
    anchor="w"
).pack(
    side="left"
)


angle_entry = tk.Entry(
    angle_frame,
    width=8,
    bg=PANEL2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    justify="center"
)

angle_entry.insert(
    0,
    "35.3"
)

angle_entry.pack(
    side="left"
)

tk.Label(
    angle_frame,
    text=" °",
    bg=PANEL,
    fg=MUTED
).pack(
    side="left"
)


update_position_button = tk.Button(
    control,
    text="APPLY POSITION",
    command=update_position_from_fields,
    bg=PANEL2,
    fg=TEXT,
    activebackground="#2a3038",
    activeforeground=TEXT,
    relief="flat"
)

update_position_button.pack(
    fill="x",
    padx=18,
    pady=8
)


distance_entry.bind(
    "<Return>",
    update_position_from_fields
)

angle_entry.bind(
    "<Return>",
    update_position_from_fields
)


# ============================================================
# ANIMATION
# ============================================================

panel_title(
    control,
    "ANIMATION"
)


animation_var = tk.StringVar(
    value="Manuaalinen"
)


animation_menu = tk.OptionMenu(
    control,
    animation_var,
    *ANIMATIONS,
    command=animation_changed
)

animation_menu.config(
    bg=PANEL2,
    fg=TEXT,
    activebackground=PANEL2,
    activeforeground=TEXT,
    highlightthickness=0,
    relief="flat"
)

animation_menu["menu"].config(
    bg=PANEL2,
    fg=TEXT
)

animation_menu.pack(
    fill="x",
    padx=18,
    pady=4
)


# ============================================================
# CUSTOM ORBIT
# ============================================================

custom_orbit_frame = tk.Frame(
    control,
    bg=PANEL
)

custom_orbit_frame.pack(
    fill="x",
    padx=18,
    pady=4
)


tk.Label(
    custom_orbit_frame,
    text="Custom orbit",
    bg=PANEL,
    fg=MUTED
).pack(
    side="left"
)


custom_orbit_entry = tk.Entry(
    custom_orbit_frame,
    width=7,
    bg=PANEL2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    justify="center"
)

custom_orbit_entry.insert(
    0,
    "3.0"
)

custom_orbit_entry.pack(
    side="right"
)

custom_orbit_entry.bind(
    "<Return>",
    custom_orbit_changed
)

custom_orbit_entry.bind(
    "<FocusOut>",
    custom_orbit_changed
)


# ============================================================
# ANIMATION SPEED
# ============================================================

panel_title(
    control,
    "ANIMATION SPEED"
)


speed_frame = tk.Frame(
    control,
    bg=PANEL
)

speed_frame.pack(
    fill="x",
    padx=18
)


animation_speed_entry = tk.Entry(
    speed_frame,
    width=7,
    bg=PANEL2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    justify="center",
    font=(
        "Consolas",
        11
    )
)

animation_speed_entry.insert(
    0,
    "1.00"
)

animation_speed_entry.pack(
    side="left"
)


tk.Label(
    speed_frame,
    text=" ×",
    bg=PANEL,
    fg=MUTED
).pack(
    side="left"
)


animation_speed_slider = tk.Scale(
    control,
    from_=0.05,
    to=20.0,
    resolution=0.05,
    orient="horizontal",
    command=animation_speed_changed,
    bg=PANEL,
    fg=TEXT,
    troughcolor=PANEL2,
    highlightthickness=0,
    showvalue=False,
    length=250
)

animation_speed_slider.set(
    1.0
)

animation_speed_slider.pack(
    padx=15,
    pady=8
)


animation_speed_entry.bind(
    "<Return>",
    animation_speed_entry_changed
)

animation_speed_entry.bind(
    "<FocusOut>",
    animation_speed_entry_changed
)


animation_status = tk.Label(
    control,
    text="● MANUAALINEN",
    bg=PANEL,
    fg=MUTED,
    font=(
        "Segoe UI",
        9,
        "bold"
    )
)

animation_status.pack(
    pady=4
)


# ============================================================
# RIGHT CANVAS
# ============================================================

canvas_frame = tk.Frame(
    main,
    bg=BG
)

canvas_frame.pack(
    side="left",
    fill="both",
    expand=True
)


canvas = tk.Canvas(
    canvas_frame,
    bg=BG,
    highlightthickness=0
)

canvas.pack(
    fill="both",
    expand=True
)


canvas.bind(
    "<Button-1>",
    mouse_down
)

canvas.bind(
    "<B1-Motion>",
    mouse_move
)

canvas.bind(
    "<ButtonRelease-1>",
    mouse_up
)


canvas.bind(
    "<Configure>",
    lambda event: update_canvas()
)


# ============================================================
# INFO PANEL
# ============================================================

info = tk.Frame(
    canvas_frame,
    bg=PANEL2,
    height=100
)

info.pack(
    fill="x"
)

info.pack_propagate(
    False
)


def create_info_item(
    parent,
    title
):

    frame = tk.Frame(
        parent,
        bg=PANEL2
    )

    frame.pack(
        side="left",
        expand=True,
        fill="both"
    )

    tk.Label(
        frame,
        text=title,
        bg=PANEL2,
        fg=MUTED,
        font=(
            "Segoe UI",
            8
        )
    ).pack(
        pady=8
    )

    value = tk.Label(
        frame,
        text="--",
        bg=PANEL2,
        fg=TEXT,
        font=(
            "Consolas",
            12,
            "bold"
        )
    )

    value.pack()

    return value


distance_value = create_info_item(
    info,
    "DISTANCE"
)

angle_value = create_info_item(
    info,
    "ANGLE"
)

itd_value = create_info_item(
    info,
    "ITD"
)

left_value = create_info_item(
    info,
    "LEFT GAIN"
)

right_value = create_info_item(
    info,
    "RIGHT GAIN"
)

attenuation_value = create_info_item(
    info,
    "DISTANCE GAIN"
)


# ============================================================
# BOTTOM STATUS
# ============================================================

bottom = tk.Frame(
    root,
    bg=PANEL,
    height=32
)

bottom.pack(
    fill="x"
)

bottom.pack_propagate(
    False
)


status_label = tk.Label(
    bottom,
    text="Valmis",
    bg=PANEL,
    fg=MUTED,
    anchor="w",
    padx=15
)

status_label.pack(
    side="left",
    fill="y"
)


tk.Label(
    bottom,
    text=(
        "Drag speaker • "
        "Front 0° • Right +90° • Back 180° • Left -90°"
    ),
    bg=PANEL,
    fg=MUTED
).pack(
    side="right",
    padx=15
)


# ============================================================
# INITIALIZATION
# ============================================================

update_file_label()
update_play_button()
update_canvas()
update_info()

animation_loop()
information_loop()


# ============================================================
# CLOSE
# ============================================================

root.protocol(
    "WM_DELETE_WINDOW",
    close_audio
)


# ============================================================
# START
# ============================================================

root.mainloop()
