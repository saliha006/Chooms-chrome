"""Pix's speaker and mic on Harry's laptop, for run.py on the Intel laptop.

For when the Intel laptop has no speaker (docs/station.md 2c). Keeps two SSH pipes open, reconnecting forever:
  Intel /tmp/pix-speaker  ->  this laptop's speaker   (raw S16LE mono 22050 Hz)
  this laptop's mic       ->  Intel /tmp/pix-mic      (raw S16LE mono 16000 Hz)
The FIFOs are PipeWire pipe-tunnel devices set as the Intel laptop's defaults
(90-pix-remote-audio.conf in this folder), so aplay/arecord in run.py use them unchanged.

  pythonw narrator/remote_audio/link.py     on Harry's laptop; a second copy exits at once
Log: runs/pix-audio.log.
"""
import logging
import socket
import subprocess
import threading
import time
from pathlib import Path

import sounddevice

HOST = "intel@10.0.41.130"
SSH = ["C:/Windows/System32/OpenSSH/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
       "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2", HOST]
SPEAKER_RATE = 22_050
MIC_RATE = 16_000
BLOCK_S = 0.05
LOCK_PORT = 47_651  # a second copy would split the speaker FIFO's audio between two readers
NO_WINDOW = 0x08000000

# A reader or writer left over from a dropped connection would steal or interleave audio; the pidfile lets the
# new one stop it ($$ becomes cat's pid through exec). Never pkill -f: the pattern sits in this shell's own command line.
SPEAKER_CMD = ("kill $(cat /tmp/pix-speaker.pid 2>/dev/null) 2>/dev/null; echo $$ > /tmp/pix-speaker.pid; "
               "exec cat /tmp/pix-speaker")
MIC_CMD = "kill $(cat /tmp/pix-mic.pid 2>/dev/null) 2>/dev/null; echo $$ > /tmp/pix-mic.pid; exec cat > /tmp/pix-mic"

log = logging.getLogger("pix-audio")


def speaker() -> None:
    block = int(SPEAKER_RATE * BLOCK_S) * 2
    while True:
        ssh = None
        try:
            ssh = subprocess.Popen([*SSH, SPEAKER_CMD], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
            log.info("speaker connecting")
            with sounddevice.RawOutputStream(samplerate=SPEAKER_RATE, channels=1, dtype="int16") as out:
                while chunk := ssh.stdout.read(block):
                    out.write(chunk[: len(chunk) // 2 * 2])
            log.warning("speaker link closed")
        except Exception as exc:
            log.warning("speaker link failed: %s", exc)
        if ssh is not None:
            ssh.kill()
        time.sleep(2)


def mic() -> None:
    frames = int(MIC_RATE * BLOCK_S)
    while True:
        ssh = None
        try:
            ssh = subprocess.Popen([*SSH, MIC_CMD], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
            log.info("mic connecting")
            with sounddevice.RawInputStream(samplerate=MIC_RATE, channels=1, dtype="int16", blocksize=frames) as stream:
                while ssh.poll() is None:
                    data, _ = stream.read(frames)
                    ssh.stdin.write(bytes(data))
                    ssh.stdin.flush()
            log.warning("mic link closed")
        except Exception as exc:
            log.warning("mic link failed: %s", exc)
        if ssh is not None:
            ssh.kill()
        time.sleep(2)


def main() -> None:
    logging.basicConfig(filename=Path(__file__).resolve().parents[2] / "runs" / "pix-audio.log", level=logging.INFO,
                        format="%(asctime)s %(message)s")
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        log.info("already running, exiting")
        return
    log.info("starting, host %s", HOST)
    threading.Thread(target=speaker, daemon=True).start()
    mic()


if __name__ == "__main__":
    main()
