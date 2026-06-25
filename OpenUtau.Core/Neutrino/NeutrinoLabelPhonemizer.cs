using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using OpenUtau.Api;
using OpenUtau.Core.Hts;
using OpenUtau.Core.Ustx;
using OpenUtau.Core.Util;
using Serilog;

namespace OpenUtau.Core.Neutrino {
    [Phonemizer("Neutrino Label Phonemizer", "NEUTRINO")]
    public class NeutrinoLabelPhonemizer : HTSLabelPhonemizer {
        string NeutrinoExe = string.Empty;
        string NeutrinoClientExe = string.Empty;
        string NeutrinoServerExe = string.Empty;
        string NsfExe = string.Empty;
        string WorldExe = string.Empty;

        protected new NeutrinoSinger singer;

        List<string> macronLyrics = new List<string>();

        public override void SetSinger(USinger singer) {
            this.singer = singer as NeutrinoSinger;
            if (this.singer == null) {
                return;
            }
            lang = "JPN";//TODO: use singer.language
            string confPath = "japanese.utf_8.conf";
            tablePath = "japanese.utf_8.table";
            string basePath = Path.Join(PathManager.Inst.DependencyPath, "NEUTRINO");
            if (!Directory.Exists(basePath)) {
                // v2.x 通用
                if (this.singer.singerVersion.StartsWith("v2")) {
                    string v2Path = Path.Join(PathManager.Inst.DependencyPath, "NEUTRINO_v2");
                    if (Directory.Exists(v2Path)) {
                        basePath = v2Path;
                    } else {
                        // fallback：兼容旧的 v27 目录名
                        string v27Path = Path.Join(PathManager.Inst.DependencyPath, "NEUTRINO_v27");
                        if (Directory.Exists(v27Path)) {
                            basePath = v27Path;
                        }
                    }
                }
                // v3.x 通用
                else if (this.singer.singerVersion.StartsWith("v3")) {
                    basePath = Path.Join(PathManager.Inst.DependencyPath, "NEUTRINO_v3");
                }
            }
            //Load Dictionary
            try {
                phoneDict.Clear();
                LoadDict(Path.Join(basePath, "settings", "dic", confPath), Encoding.UTF8);
                LoadDict(Path.Join(basePath, "settings", "dic", tablePath), Encoding.UTF8);
                // Lyrics often handled in OpenUtau
                phoneDict.Add("R", new string[] { "pau" });
                phoneDict.Add("-", new string[] { "pau" });
                phoneDict.Add("SP", new string[] { "pau" });
                phoneDict.Add("AP", new string[] { "br" });
                g2p = this.LoadG2p();
            } catch (Exception e) {
                Log.Error(e, $"failed to load dictionary from {tablePath}");
                return;
            }
            if (OS.IsWindows()) {
                NeutrinoExe = Path.Join(basePath, @"bin", "NEUTRINO.exe");
                NeutrinoClientExe = Path.Join(basePath, @"bin", "neutrino_client.exe");
                NeutrinoServerExe = Path.Join(basePath, @"bin", "neutrino_server.exe");
            } else if (OS.IsMacOS() || OS.IsLinux()) {
                NeutrinoExe = Path.Join(basePath, @"bin", "NEUTRINO");
            } else {
                throw new NotSupportedException("Platform not supported.");
            }
            NeutrinoServerLauncher.EnsureStarted(NeutrinoServerExe);
        }
        protected IG2p LoadG2p() {
            var g2ps = new List<IG2p>();
            var builder = G2pDictionary.NewBuilder();
            if (!phoneDict.ContainsKey("VOWELS") || !phoneDict.ContainsKey("SILENCES")) {
                return new G2pFallbacks(g2ps.ToArray());
            }
            vowels.AddRange(phoneDict["VOWELS"]);
            breaks.AddRange(phoneDict.GetValueOrDefault("BREAK", Array.Empty<string>()));
            pauses.AddRange(phoneDict.GetValueOrDefault("PAUSES", Array.Empty<string>()));
            silences.AddRange(phoneDict["SILENCES"]);
            consonants.AddRange(phoneDict.GetValueOrDefault("PHONEME_CL", Array.Empty<string>()));
            macronLyrics.AddRange(phoneDict.GetValueOrDefault("MACRON", Array.Empty<string>()));
            foreach (var dict in phoneDict.Values) {
                foreach (var phoneme in dict) {
                    if (!consonants.Contains(phoneme) && !vowels.Contains(phoneme) &&
                        !breaks.Contains(phoneme) && !pauses.Contains(phoneme) &&
                        !silences.Contains(phoneme)) {
                        consonants.Add(phoneme);
                    }
                    if (!consonants.Contains(phoneme)) {
                        builder.AddSymbol(phoneme, true);
                    } else {
                        builder.AddSymbol(phoneme, false);
                    }
                }
            }
            foreach (var entry in phoneDict.Keys) {
                builder.AddEntry(entry, phoneDict[entry]);
                foreach (var reduction in phoneDict.GetValueOrDefault("VOWEL_REDUCTION", Array.Empty<string>())) {
                    var phonemes = phoneDict[entry].Except(vowels).ToList();
                    if (phonemes.Count == 0) continue;
                    builder.AddEntry(entry + reduction, phonemes);
                }
                foreach (var macron in phoneDict.GetValueOrDefault("MACRON", Array.Empty<string>())) {
                    var addPhonemes = phoneDict[entry].Where(x => vowels.Contains(x)).ToList();
                    if (addPhonemes.Count == 0) continue;
                    var phonemes = phoneDict[entry].ToList();
                    phonemes.AddRange(addPhonemes);
                    builder.AddEntry(entry + macron, phonemes);
                    macronLyrics.Add(entry + macron);
                }
            }
            g2ps.Add(builder.Build());
            return new G2pFallbacks(g2ps.ToArray());
        }

        protected override Note[][] PhraseAdjustments(Note[][] phrese) {
            if (g2p == null || !phoneDict.ContainsKey("MACRON")) {
                return phrese;
            }
            for (int i = 0; i < phrese.Length; i++) {
                var lyric = phrese[i][0].lyric;
                if (phoneDict["MACRON"].Contains(lyric) && (i > 0)) {
                    if (g2p.IsValidSymbol(lyric)) {
                        var vowel = g2p.Query(phrese[i - 1][0].lyric).FirstOrDefault(phoneme => vowels.Contains(phoneme));
                        if (!string.IsNullOrEmpty(vowel)) {
                            phrese[i][0].lyric = vowel;
                        }
                    }
                }
            }
            return phrese;
        }

        protected override HTSNote CustomHTSNoteContext(HTSNote htsNote, Note note) {
            var fixs = GetPrefixAndSuffix(note);
            if (!htsNote.isRest && !htsNote.isSlur) {
                htsNote.langDependent = "0"; // no macron
                if (macronLyrics.Contains(note.lyric)) {
                    htsNote.langDependent = "1"; // macron
                }
            }
            return htsNote;
        }

        protected override HTSPhoneme[] CustomHTSPhonemeContext(HTSPhoneme[] htsPhonemes, Note[] notes) {
            var fixs = GetPrefixAndSuffix(notes[0]);
            foreach (var htsPhoneme in htsPhonemes) {
                htsPhoneme.flag1 = "00"; // NEUTRINO Default.
            }
            return htsPhonemes;
        }

        protected override void SendScore(Note[][] phrase) {
            if (this.singer.singerVersion == null) {
                return;
            }
            if (File.Exists(fullScorePath) && !File.Exists(monoTimingPath)) {
                var voicebankNameHash = $"{this.singer.voicebankNameHash:x16}";
                string f0Path = Path.Join(htstmpPath, $"{voicebankNameHash}_tmp.f0");
                string melspecPath = Path.Join(htstmpPath, $"{voicebankNameHash}_tmp.melspec");
                string wavPath = Path.Join(htstmpPath, $"{voicebankNameHash}_tmp.wav");
                string modelDir = this.singer.modelDir + "/";
                var attr = phrase[0][0].phonemeAttributes?.FirstOrDefault(attr => attr.index == 0) ?? default;
                int toneShift = attr.toneShift;
                int numThreads = Preferences.Default.NumRenderThreads;
                string ArgParam = string.Empty;
                if (this.singer.singerVersion.StartsWith("v2")) {
                    // v2.x 通用（v2.3、v2.7 等）
                    // 注意：v2 的 NEUTRINO.exe 用 -o 表示线程数（不是 -p）
                    ArgParam = $"\"{fullScorePath}\" \"{monoTimingPath}\" \"{f0Path}\" \"{melspecPath}\" \"{modelDir}\" -k {toneShift} -d 3 -n 1 -o {numThreads} -m -t";
                } else if (this.singer.singerVersion.StartsWith("v3")) {
                    // v3.x 通用（v3.0、v3.1 等）
                    //TODO: -S support model
                    ArgParam = $"\"{fullScorePath}\" \"{monoTimingPath}\" \"{f0Path}\" \"{melspecPath}\" \"{wavPath}\" \"{modelDir}\" --skip-f0 --skip-melspec --skip-wav -n {numThreads} -f {toneShift} -m -t";
                } else {
                    Log.Error($"Unsupported NEUTRINO version: {this.singer.singerVersion}");
                    return;
                }
                Log.Information($"NEUTRINO timing args: {ArgParam}");
                if (File.Exists(NeutrinoClientExe)) {
                    ProcessRunner.Run(NeutrinoClientExe, ArgParam, Log.Logger);
                } else {
                    ProcessRunner.Run(NeutrinoExe, ArgParam, Log.Logger);
                }
            }
        }
    }
}