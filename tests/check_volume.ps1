param([string]$HostPath = (Join-Path $PSScriptRoot '../AudioHost.exe'))
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Reflection;
using System.Runtime.InteropServices;
public static class PbzVolumeCheck {
    public static void Run(string path) {
        var assembly=Assembly.LoadFile(path);
        var type=assembly.GetType("AudioHost+Voice",true);
        var input=new short[]{10000,-10000,32767,-32768};
        var pcm=new byte[input.Length*2];
        Buffer.BlockCopy(input,0,pcm,0,pcm.Length);
        // Prepare a real WinMM buffer but never submit it: no audition.
        object voice=Activator.CreateInstance(type,new object[]{pcm,0,0L,true,100});
        try {
            var set=type.GetMethod("SetVolume");
            var pointer=type.GetField("data",BindingFlags.Instance|BindingFlags.NonPublic);
            foreach(int volume in new[]{100,50,0,200,0}) {
                set.Invoke(voice,new object[]{volume});
                var buffer=new byte[pcm.Length];
                Marshal.Copy((IntPtr)pointer.GetValue(voice),buffer,0,buffer.Length);
                for(int i=0;i<input.Length;i++) {
                    int expected=Math.Max(short.MinValue,Math.Min(short.MaxValue,input[i]*volume/100));
                    if(BitConverter.ToInt16(buffer,i*2)!=expected)
                        throw new Exception("Unexpected PCM sample at volume "+volume);
                }
            }
        } finally { ((IDisposable)voice).Dispose(); }
    }
}
'@
[PbzVolumeCheck]::Run((Resolve-Path -LiteralPath $HostPath).Path)
Write-Output 'PASS real prepared PCM buffer: 100/50/0/200/0 percent, zero is all-zero samples, saturation correct; no audio submitted'
