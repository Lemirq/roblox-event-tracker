set flagFile to "/tmp/autoclicker_running"

if (do shell script "test -f " & flagFile & " && echo yes || echo no") is "no" then
    do shell script "touch " & flagFile
    do shell script "nohup sh -c 'while [ -f " & flagFile & " ]; do cliclick c:. ; sleep 0.01; done' >/dev/null 2>&1 &"
else
    do shell script "rm " & flagFile
end if
