#!/usr/bin/env python3
import sys
import os
import argparse
import youtube_dl
import subprocess
import pysubs2
import json
import pprint
import chat_downloader

def ytdl(url):
    ydl_opts = {
        "outtmpl": "%(title)s-%(id)s.%(ext)s",
        "merge_output_format": "mkv"
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url)
        return result, ydl.prepare_filename(result)

def ytdl_comments(url, jsonname):
    chat_downloader.run(url=url, output=jsonname, quiet=True)
    return True

def convert_yt_comments(jsonname, comment_duration, video_info, outputname):
    with open(jsonname) as f:
        yt_comments = json.load(f)

    if len(yt_comments) == 0:
        return

    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = 384
    subs.info["PlayResY"] = 288

    start_time_shift = yt_comments[0]["time_in_seconds"] * 1000

    comment_channel = []
    comment_size = 20
    for i in range(0, subs.info["PlayResY"], comment_size):
        comment_channel.append(None)

    for msg in yt_comments:
        now = msg["time_in_seconds"] * 1000
        if now > video_info["duration"] * 1000:
#            print(now, ">", video_info["duration"] * 1000)
            continue

        if not msg["message"]:
            continue

        selected_channel = 1
        for index, chan in enumerate(comment_channel):
            if (not chan or
                chan["time_in_seconds"] * 1000 + (200 * len(msg["message"])) < now):
                comment_channel[index] = msg
                selected_channel = index + 1
                break

        movement = ("{\move(414," + str(selected_channel * 20) +
                    ",-30," + str(selected_channel * 20) +
                    ",0," + str(comment_duration) +
                    ")}")

        subs.append(pysubs2.SSAEvent(start=pysubs2.make_time(ms=msg["time_in_seconds"] * 1000),
                                     end=pysubs2.make_time(ms=(msg["time_in_seconds"] * 1000) + comment_duration),
                                     text=movement+msg["message"]))

    subs.shift(ms=-start_time_shift+100)
    subs.save(outputname)

def main(args):
    for url in args.urls:
        result, vid_filename = ytdl(url)
        id = result["id"]
        os.rename(vid_filename, id + ".mkv")

        print("[danmaku] Downloading live comments")
        ok = ytdl_comments(url, id + ".json")
        if not ok:
            print("[danmaku] cannot download live comments")
            continue

        print("[danmaku] converting to .ass")
        convert_yt_comments(id + ".json", args.duration, result, id + ".ass")

        print("[danmaku] adding .ass to mkv")
        try:
            subprocess.run(["mkvmerge",
                            "--output", vid_filename,
                            id + ".mkv",
                            "--track-name", "0:youtube-comments",
                            id + ".ass"])

        except FileNotFoundError:
            print("[danmaku] mkvmerge not found. Use ffmpeg.")

            subprocess.run(["ffmpeg",
                            "-i", id + ".mkv",
                            "-i", id + ".ass",
                            "-c:a", "copy",
                            "-c:v", "copy",
                            "-map", "0",
                            "-map", "1",
                            "-hide_banner",
                            "-loglevel", "panic",
                            "-y",
                            vid_filename])

        os.remove(id + ".mkv")
        os.remove(id + ".json")
        os.remove(id + ".ass")

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=5000, help="comment display duration")
    parser.add_argument("urls", nargs='*', type=str)
    return parser

if __name__ == "__main__":
    parser = get_parser()
    main(parser.parse_args())
