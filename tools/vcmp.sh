#/bin/bash

set -x

fleft=$1
fright=$2
mode=$3

if [ ${mode} == "diff" ]
then
ffmpeg.exe -i ${fleft} -i ${fright} -filter_complex \
"[0:v][1:v]blend=all_mode=difference[dif];"\
"[dif]split[dif1][dif2];[dif1]unsharp=luma_amount=5[dif3];[dif2][dif3]hstack[top];"\
"[0:v][1:v]hstack[bottom];[top][bottom]vstack,format=yuv420p" \
-c:v rawvideo -f  matroska - | \
ffplay.exe - -loop 10 -fs
elif [ ${mode} == "hconcat" ]
then
ffmpeg.exe -i ${fleft} -i ${fright} -filter_complex \
"[0:v]crop=iw/2:ih:0:0,pad=(iw+2):ih:0:0[c1];"\
"[1:v]crop=iw/2:ih:iw/2:0[c2];"\
"[c1][c2]hstack,format=yuv420p" \
-c:v rawvideo -f  matroska - | \
ffplay.exe - -loop 10 -fs
else
ffmpeg.exe -i ${fleft} -i ${fright} -filter_complex \
"[0:v]crop=iw:ih/2:0:0,pad=iw:(ih+2):0:0[c1];"\
"[1:v]crop=iw:ih/2:0:ih/2[c2];"\
"[c1][c2]vstack,format=yuv420p" \
-c:v rawvideo -f  matroska - | \
ffplay.exe - -loop 10 -fs

fi
