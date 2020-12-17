#!/usr/bin/env python3
import sys
import os
import argparse
import youtube_dl
import subprocess
import pysubs2
import json
import pprint

CHAT_DL_PATH="/Users/hare1039/Documents/gitprojects/chat-replay-downloader"

def ytdl(url):
    ydl_opts = {
        "outtmpl": "%(id)s.%(ext)s",
        "merge_output_format": "mkv"
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url)

def ytdl_comments(url, jsonname):
    r = subprocess.run(["python3",
                        CHAT_DL_PATH + "/chat_replay_downloader.py",
                        "-output", jsonname,
                        "-message_type", "all",
                        "--hide_output",
                        url])
    return r.returncode == 0

def convert_yt_comments(jsonname, comment_duration, outputname):
    with open(jsonname) as f:
        yt_comments = json.load(f)

    if len(yt_comments) == 0:
        return

    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = 384
    subs.info["PlayResY"] = 288

    start_time_shift = yt_comments[0]["video_offset_time_msec"]

    comment_count = []
    for msg in yt_comments:
        now = msg["video_offset_time_msec"]

        if not msg["message"]:
            continue

        new_count = []
        for c in comment_count:
            if c["video_offset_time_msec"] > now - 1000:
                new_count.append(c)

        comment_count = new_count
        comment_count.append(msg)

        movement = ("{\move(384," + str(len(comment_count) * 20) +
                    ",0," + str(len(comment_count) * 20) +
                    ",0," + str(comment_duration) +
                    ")}")
        subs.append(pysubs2.SSAEvent(start=pysubs2.make_time(ms=msg["video_offset_time_msec"]),
                                     end=pysubs2.make_time(ms=msg["video_offset_time_msec"] + comment_duration),
                                     text=movement+msg["message"]))

    subs.shift(ms=-start_time_shift+100)
    subs.save(outputname)

def main(args):
    for url in args.urls:
        result = ytdl(url)
        id = result["id"]

        ok = ytdl_comments(url, id + ".json")
        if not ok:
            print("cannot download live comments")
            continue

        convert_yt_comments(id + ".json", args.duration, id + ".ass")

        subprocess.run(["ffmpeg",
                        "-i", id + ".mkv",
                        "-i", id + ".ass",
                        "-c:a", "copy",
                        "-c:v", "copy",
                        "-map", "0",
                        "-map", "1",
                        "-hide_banner",
                        "-loglevel", "panic",
                        result["title"] + "-" + id + ".mkv"])

        os.remove(id + ".mkv")
        os.remove(id + ".json")
        os.remove(id + ".ass")

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, help="start")
    parser.add_argument("--duration", type=int, default=5000, help="comment display duration")
    parser.add_argument("urls", nargs='*', type=str)
    return parser

if __name__ == "__main__":
    parser = get_parser()
    main(parser.parse_args())
