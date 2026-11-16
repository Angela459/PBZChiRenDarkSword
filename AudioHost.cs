using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Runtime.InteropServices;

// Independent PCM voices; full-charge hits cancel only their cast's ground clip.
internal static class AudioHost
{
    [StructLayout(LayoutKind.Sequential, Pack=2)]
    struct Format { public ushort tag, channels; public uint rate, bytesPerSecond; public ushort block, bits, extra; }
    [StructLayout(LayoutKind.Sequential)]
    struct Header { public IntPtr data; public uint length, recorded; public UIntPtr user; public uint flags, loops; public IntPtr next; public UIntPtr reserved; }
    [DllImport("winmm.dll")] static extern int waveOutOpen(out IntPtr handle, uint device, ref Format format, IntPtr callback, IntPtr instance, uint flags);
    [DllImport("winmm.dll")] static extern int waveOutPrepareHeader(IntPtr handle, IntPtr header, uint size);
    [DllImport("winmm.dll")] static extern int waveOutWrite(IntPtr handle, IntPtr header, uint size);
    [DllImport("winmm.dll")] static extern int waveOutReset(IntPtr handle);
    [DllImport("winmm.dll")] static extern int waveOutUnprepareHeader(IntPtr handle, IntPtr header, uint size);
    [DllImport("winmm.dll")] static extern int waveOutClose(IntPtr handle);
    sealed class Voice : IDisposable
    {
        IntPtr handle, data, header;
        bool playing;
        public readonly int Clip;
        public readonly long Cast;
        public readonly bool Reusable;
        public bool Busy { get { return playing; } }
        static readonly uint Size = (uint)Marshal.SizeOf(typeof(Header));
        public Voice(byte[] samples, int clip=0, long cast=0, bool prepareOnly=false)
        {
            Clip=clip; Cast=cast; Reusable=prepareOnly;
            var format = new Format {tag=1, channels=1, rate=48000, bytesPerSecond=96000, block=2, bits=16};
            try {
                int error = waveOutOpen(out handle, UInt32.MaxValue, ref format, IntPtr.Zero, IntPtr.Zero, 0);
                if (error != 0) throw new Exception("waveOutOpen " + error);
                data=Marshal.AllocHGlobal(samples.Length); Marshal.Copy(samples,0,data,samples.Length);
                header=Marshal.AllocHGlobal((int)Size);
                Marshal.StructureToPtr(new Header {data=data,length=(uint)samples.Length},header,false);
                error=waveOutPrepareHeader(handle,header,Size);
                if (error != 0) throw new Exception("waveOutPrepareHeader " + error);
                if(!prepareOnly) Play();
            } catch { Dispose(); throw; }
        }
        public void Play()
        {
            if(playing || handle==IntPtr.Zero) throw new Exception("voice is busy or closed");
            int error=waveOutWrite(handle,header,Size);
            if(error!=0) throw new Exception("waveOutWrite " + error);
            playing=true;
        }
        public void Release()
        {
            if(playing && !Done) waveOutReset(handle);
            playing=false;
        }
        public bool Done { get { return header==IntPtr.Zero || (((Header)Marshal.PtrToStructure(header,typeof(Header))).flags & 1)!=0; } }
        public void Dispose()
        {
            if (handle!=IntPtr.Zero) {
                waveOutReset(handle);
                if(header!=IntPtr.Zero) waveOutUnprepareHeader(handle,header,Size);
                waveOutClose(handle); handle=IntPtr.Zero;
            }
            if(header!=IntPtr.Zero) { Marshal.FreeHGlobal(header); header=IntPtr.Zero; }
            if(data!=IntPtr.Zero) { Marshal.FreeHGlobal(data); data=IntPtr.Zero; }
        }
    }
    static readonly DateTime Epoch=new DateTime(1970,1,1,0,0,0,DateTimeKind.Utc);
    static long Now() { return (long)(DateTime.UtcNow-Epoch).TotalSeconds; }
    static byte[] ReadPcm(string path)
    {
        using(var r=new BinaryReader(File.OpenRead(path))) {
            if(new string(r.ReadChars(4))!="RIFF") throw new Exception("not RIFF");
            r.ReadUInt32(); if(new string(r.ReadChars(4))!="WAVE") throw new Exception("not WAVE");
            bool fmt=false;
            while(r.BaseStream.Position+8<=r.BaseStream.Length) {
                string chunk=new string(r.ReadChars(4)); uint size=r.ReadUInt32(); long end=r.BaseStream.Position+size;
                if(end>r.BaseStream.Length) throw new Exception("truncated WAV");
                if(chunk=="fmt ") {
                    ushort tag=r.ReadUInt16(),ch=r.ReadUInt16(); uint rate=r.ReadUInt32();
                    r.ReadUInt32(); r.ReadUInt16(); ushort bits=r.ReadUInt16();
                    if(tag!=1 || ch!=1 || rate!=48000 || bits!=16) throw new Exception("expected PCM mono 48kHz 16bit");
                    fmt=true;
                }
                if(chunk=="data") { if(!fmt) throw new Exception("missing PCM format"); return r.ReadBytes((int)size); }
                r.BaseStream.Position=end+(size%2);
            }
            throw new Exception("missing WAV data");
        }
    }
    static void Write(string path,string value)
    {
        string temp=path+".host-tmp";
        File.WriteAllText(temp,value,new UTF8Encoding(false));
        if(File.Exists(path)) File.Replace(temp,path,null); else File.Move(temp,path);
    }
    static void Log(string path,string value) { File.AppendAllText(path,DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff")+" "+value+"\r\n"); }
    static string ReadShared(string path)
    {
        // File.ReadAllText denies concurrent writers on Windows. Lua publishes
        // heartbeat/commands with fopen("w"), so readers must allow write/delete.
        using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
        using(var reader=new StreamReader(file)) return reader.ReadToEnd();
    }
    static void Stop(List<Voice> voices) { foreach(var v in voices) { if(v.Reusable) v.Release(); else v.Dispose(); } voices.Clear(); }
    static int StopGround(List<Voice> voices,long cast)
    {
        int stopped=0;
        for(int i=voices.Count-1;i>=0;i--) {
            if(voices[i].Clip!=4 || (cast!=0 && voices[i].Cast!=cast)) continue;
            voices[i].Dispose(); voices.RemoveAt(i); stopped++;
        }
        return stopped;
    }
    [STAThread] static int Main(string[] args)
    {
        if(args.Length!=2) return 2;
        string dir=Path.GetFullPath(args[0]),session=args[1];
        if(!System.Text.RegularExpressions.Regex.IsMatch(session,@"^[0-9-]+$")) return 3;
        Directory.CreateDirectory(dir);
        string log=Path.Combine(dir,"host-"+session+".log");
        var voices=new List<Voice>();
        var hitVoices=new List<Voice>();
        var hitCasts=new HashSet<long>();
        using(var mutex=new Mutex(false,"Local\\PBZChiRenAudio-"+session)) {
            if(!mutex.WaitOne(0)) return 0;
            try {
                var clips=new List<byte[]>();
                foreach(string file in new[]{"1_10.wav","2_02.wav","3_09.wav","4_01.wav","5_12.wav","6_11.wav"})
                    clips.Add(ReadPcm(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"Audio",file)));
                // A single PCM buffer guarantees 12 finishes before 11 begins,
                // without polling gaps, duration guesses, or truncation.
                byte[] hitSequence=new byte[clips[4].Length+clips[5].Length];
                Buffer.BlockCopy(clips[4],0,hitSequence,0,clips[4].Length);
                Buffer.BlockCopy(clips[5],0,hitSequence,clips[4].Length,clips[5].Length);
                // Open devices and prepare fixed hit buffers before gameplay.
                // Idle prepared headers emit no sound; a hit only submits data.
                for(int i=0;i<4;i++) hitVoices.Add(new Voice(hitSequence,0,0,true));
                long heartbeat=Now(),readyAt=0,lastSequence=0;
                Log(log,"READY v0.12 session="+session+" independent_clips=10,02,09,01 hit_sequence=12,11 cancels_same_cast_01=true prewarmed_hit_voices="+hitVoices.Count);
                bool quit=false;
                while(!quit && Now()-heartbeat<=30) {
                    try {
                        string beatPath=Path.Combine(dir,"heartbeat.txt");
                        string[] hb=File.Exists(beatPath)?ReadShared(beatPath).Trim().Split('|'):new string[0]; long at;
                        if(hb.Length==2 && hb[0]==session && long.TryParse(hb[1],out at) && Math.Abs(Now()-at)<=30) heartbeat=at;
                        if(Now()!=readyAt) { readyAt=Now(); Write(Path.Combine(dir,"ready.txt"),session+"|ready|"+readyAt); }
                        string path=Path.Combine(dir,"command.txt");
                        string text=File.Exists(path)?ReadShared(path):"";
                        // A complete newline is the publication marker. Partial writes wait for the next tick.
                        foreach(string line in text.Split('\n')) {
                            string[] p=line.Trim().Split('|'); long seq;
                            if(p.Length!=3 || p[0]!=session || !long.TryParse(p[1],out seq) || seq<=lastSequence) continue;
                            string[] action=p[2].Split(':'); long cast=0;
                            if(action.Length>2 || (action.Length==2 && (!long.TryParse(action[1],out cast) || cast<1))) continue;
                            int clip=0;
                            bool play=action[0].Length==5 && action[0].StartsWith("play") && int.TryParse(action[0].Substring(4),out clip) && clip>=1 && clip<=4;
                            bool hit=action[0]=="hit";
                            if(action.Length==2 && !hit && !(play && clip==4)) continue;
                            if(!play && !hit && action[0]!="stop" && action[0]!="quit") continue;
                            // Lua retains all recent commands, so adjacent stage messages cannot overwrite each other.
                            if(!text.EndsWith("\n") && line==text.Substring(text.LastIndexOf('\n')+1)) continue;
                            lastSequence=seq;
                            if(p[2]=="stop" || p[2]=="quit") { Stop(voices); Log(log,p[2].ToUpper()+" "+seq); }
                            if(p[2]=="quit") { quit=true; break; }
                            if(play) {
                                if(clip==4 && cast>0 && hitCasts.Contains(cast)) {
                                    Log(log,"SKIP clip=4 reason=hit cast="+cast+" command="+seq); continue;
                                }
                                if(voices.Count>=12) Stop(voices);
                                voices.Add(new Voice(clips[clip-1],clip,cast)); Log(log,"PLAY clip="+clip+" command="+seq+" cast="+cast);
                            }
                            if(hit) {
                                var timer=System.Diagnostics.Stopwatch.StartNew();
                                if(cast>0) hitCasts.Add(cast);
                                int stopped=StopGround(voices,cast);
                                int remaining=voices.Count;
                                if(voices.Count>=12) Stop(voices);
                                Voice prepared=null;
                                foreach(var voice in hitVoices) if(!voice.Busy) { prepared=voice;break; }
                                if(prepared!=null) { prepared.Play(); voices.Add(prepared); }
                                else voices.Add(new Voice(hitSequence));
                                timer.Stop();
                                Log(log,"STOP_GROUND cast="+cast+" voices="+stopped+" remaining="+remaining+" command="+seq);
                                Log(log,"PLAY sequence=12,11 command="+seq+" cast="+cast+" prepared="+(prepared!=null)+" submit_ms="+timer.Elapsed.TotalMilliseconds.ToString("F3",System.Globalization.CultureInfo.InvariantCulture));
                            }
                        }
                    } catch(IOException) { }
                    for(int i=voices.Count-1;i>=0;i--) if(voices[i].Done) {
                        if(voices[i].Reusable) voices[i].Release(); else voices[i].Dispose();
                        voices.RemoveAt(i);
                    }
                    Thread.Sleep(10);
                }
                Log(log,"EXIT"); return 0;
            } catch(Exception e) { Log(log,"ERROR "+e); return 1; }
            finally { Stop(voices); foreach(var voice in hitVoices) voice.Dispose(); mutex.ReleaseMutex(); }
        }
    }
}
