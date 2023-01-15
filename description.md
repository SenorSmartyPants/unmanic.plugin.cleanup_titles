
Select if video stream title should be copied into an empty global file title

Clear stream titles if only one stream of that type. Ex. If only one audio stream, delete its title if one exists.

Regular expression based replacements for stream titles. And optional disposition flags when matches are found. JSON formatted list regular expressions, replacement values and optional dispositions to apply to stream. **Replacements take priority over removing single stream titles**

---

#### Examples:

###### <span style="color:magenta">
1. Remove title that starts with "Original"
1. Titles that start with "Commentary" will be renamed as "Commentary" (everything after the original "Commentary" will be removed). And add `comment` flag to stream.
</span>

```
[
  {
    "pattern": "(?i)Original.*",
    "replace": ""
  },
  {
    "pattern": "(?i)Commentary.*",
    "replace": "Commentary",
    "disposition": "+comment"
  }
]
```

#### <span style="color:blue">Write your own FFmpeg params</span>
This free text input allows you to write any FFmpeg params that you want.
This is for more advanced use cases where you need finer control over the file transcode.

:::note
These params are added in three different places:
1. **MAIN OPTIONS** - After the default generic options.
   ([Main Options Docs](https://ffmpeg.org/ffmpeg.html#Main-options))
1. **ADVANCED OPTIONS** - After the input file has been specified.
   ([Advanced Options Docs](https://ffmpeg.org/ffmpeg.html#Advanced-options))

```
ffmpeg \
    -hide_banner \
    -loglevel info \
    <MAIN OPTIONS HERE> \
    -i /path/to/input/video.mkv \
    <ADVANCED OPTIONS HERE> \
    -map 0 \
    -c copy \
    -y /path/to/output/video.mkv
```
:::

---
`ffmpeg -dispositions` for a list of all available. Output from ffmpeg 5.1.2 at time of writing this document.

```
default
dub
original
comment
lyrics
karaoke
forced
hearing_impaired
visual_impaired
clean_effects
attached_pic
timed_thumbnails
captions
descriptions
metadata
dependent
still_image
```