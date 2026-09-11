"""Optional local FFmpeg bridge. Restricted demuxers; pipe-only input protocols."""
from pathlib import Path
import shutil
import subprocess

FORMATS={'.wav':'wav','.flac':'flac','.mp3':'mp3','.ogg':'ogg','.opus':'ogg','.aiff':'aiff','.aif':'aiff','.mp4':'mov','.m4a':'mov','.mov':'mov','.mkv':'matroska','.webm':'matroska','.avi':'avi','.aac':'aac'}
AUDIO=['wav','flac','mp3','ogg']
VIDEO={'.mp4','.mov','.mkv','.webm','.avi'}

def executable():
    return shutil.which('ffmpeg')

def targets(extension):
    if not executable() or extension not in FORMATS:return []
    return AUDIO+(['mp4','webm'] if extension in VIDEO else [])

def convert(source,output,target,options):
    engine=executable()
    if not engine:raise ValueError('Install local FFmpeg for media conversion; Prepare never downloads it automatically.')
    ext=Path(source).suffix.lower()
    if target not in targets(ext):raise ValueError('Unsupported media conversion.')
    codecs={'wav':['-vn','-c:a','pcm_s16le'],'flac':['-vn','-c:a','flac'],'mp3':['-vn','-c:a','libmp3lame','-b:a','160k'],'ogg':['-vn','-c:a','libvorbis','-q:a','4'],'mp4':['-c:v','libx264','-preset','fast','-crf','24','-c:a','aac','-movflags','+faststart'],'webm':['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','6','-c:a','libopus']}
    # Pass bytes through a pipe: network and local sidecar URLs cannot be opened.
    # Forced demuxer prevents playlist/concat masquerading as media input.
    args=[engine,'-nostdin','-hide_banner','-loglevel','error','-protocol_whitelist','pipe','-f',FORMATS[ext],'-i','pipe:0','-map_metadata','-1','-map_chapters','-1','-threads','2',*codecs[target],'-fs',str(100*1024*1024),'-n',output]
    result=subprocess.run(args,input=Path(source).read_bytes(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=150)
    if result.returncode:
        raise ValueError('Local media conversion failed. Codec may be unavailable, damaged, or require seekable input. No output was published.')
    # Decode produced bytes independently with the engine, same pipe restrictions.
    fmt={'mp4':'mov','webm':'matroska','ogg':'ogg'}.get(target,target)
    check=subprocess.run([engine,'-nostdin','-v','error','-protocol_whitelist','pipe','-f',fmt,'-i','pipe:0','-f','null','-'],input=Path(output).read_bytes(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=150)
    if check.returncode:raise ValueError('Converted media failed decode verification.')
    return {'warnings':['Media transcoding may lose quality, metadata, subtitle tracks and interactivity. File size is not guaranteed to decrease. Seek-dependent inputs may be rejected.'],'engine':'local FFmpeg'}
